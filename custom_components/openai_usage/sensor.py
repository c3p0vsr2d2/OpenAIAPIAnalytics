from __future__ import annotations
from datetime import date, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

# Periods and metrics
SENSOR_PERIODS = [1, 7, 30, 90, 365]
METRICS = ["cost", "requests", "input_tokens", "output_tokens"]

# Extra helper sensors (global)
EXTRA_GLOBAL_SENSORS = [
    "total_cost_all_time",   # Sum over fetched window (365 days)
    "requests_today",        # Requests today across all models
    "efficiency_cost_per_1k_tokens_last_30_days",  # cost per 1k tokens
]

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []
    data = coordinator.data

    # Build models set; coordinator.data expected to be list of records
    models = {item.get("model") for item in data if item.get("model")}
    models.add("all_models")

    # Per-model and period sensors
    for model in models:
        for metric in METRICS:
            for period in SENSOR_PERIODS:
                sensors.append(OpenAISensor(coordinator, model, metric, period, entry.entry_id))
            # Efficiency sensors per metric
            if metric in ["cost", "requests"]:
                for period in SENSOR_PERIODS:
                    sensors.append(OpenAIEfficiencySensor(coordinator, model, metric, period, entry.entry_id))

    # Extra global sensors
    for name in EXTRA_GLOBAL_SENSORS:
        sensors.append(OpenAIExtraSensor(coordinator, name, entry.entry_id))

    async_add_entities(sensors)

class OpenAISensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, model, metric, period, entry_id):
        super().__init__(coordinator)
        self.model = model
        self.metric = metric
        self.period = period
        self.entry_id = entry_id
        self._attr_name = f"OpenAI {'All Models' if model=='all_models' else model} {metric.replace('_',' ').title()} Last {period} Days"
        self._attr_unique_id = f"{entry_id}_{model}_{metric}_{period}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self.entry_id}_all_models" if self.model=="all_models" else f"{self.entry_id}_{self.model}")},
            "name": "OpenAI All Models" if self.model=="all_models" else f"OpenAI {self.model}",
            "manufacturer": "OpenAI",
            "model": "Aggregate" if self.model=="all_models" else self.model,
        }

    @property
    def native_unit_of_measurement(self):
        if "tokens" in self.metric:
            return "tokens"
        if "cost" in self.metric:
            return "$"
        if "requests" in self.metric:
            return "calls"
        return None

    @property
    def native_value(self):
        data = self.coordinator.data
        model_data = data if self.model=="all_models" else [d for d in data if d.get("model")==self.model]
        if not model_data:
            return 0

        today = date.today()
        daily_usage = {}
        for record in model_data:
            ts = record.get("aggregation_timestamp","")
            if not ts:
                continue
            day_str = ts.split("T")[0]
            if day_str not in daily_usage:
                daily_usage[day_str] = {"cost":0,"requests":0,"input_tokens":0,"output_tokens":0}
            daily_usage[day_str]["cost"] += float(record.get("cost",0))
            daily_usage[day_str]["requests"] += int(record.get("n_requests",0))
            daily_usage[day_str]["input_tokens"] += int(record.get("prompt_tokens",0))
            daily_usage[day_str]["output_tokens"] += int(record.get("completion_tokens",0))

        total = 0
        for i in range(self.period):
            day_str = (today - timedelta(days=i)).isoformat()
            if day_str in daily_usage:
                total += daily_usage[day_str].get(self.metric, 0)

        return round(total,4) if "cost" in self.metric else total

class OpenAIEfficiencySensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, model, metric, period, entry_id):
        super().__init__(coordinator)
        self.model = model
        self.metric = metric
        self.period = period
        self.entry_id = entry_id
        self._attr_name = f"OpenAI {'All Models' if model=='all_models' else model} {metric.replace('_',' ').title()} Efficiency Last {period} Days"
        self._attr_unique_id = f"{entry_id}_{model}_{metric}_eff_{period}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self.entry_id}_all_models" if self.model=="all_models" else f"{self.entry_id}_{self.model}")},
            "name": "OpenAI All Models" if self.model=="all_models" else f"OpenAI {self.model}",
            "manufacturer": "OpenAI",
            "model": "Aggregate" if self.model=="all_models" else self.model,
        }

    @property
    def native_unit_of_measurement(self):
        if self.metric == "cost":
            return "$\/token"
        if self.metric == "requests":
            return "requests\/token"
        return None

    @property
    def native_value(self):
        data = self.coordinator.data
        model_data = data if self.model=="all_models" else [d for d in data if d.get("model")==self.model]
        if not model_data:
            return 0

        today = date.today()
        daily_usage = {}
        for record in model_data:
            ts = record.get("aggregation_timestamp","" )
            if not ts:
                continue
            day_str = ts.split("T")[0]
            if day_str not in daily_usage:
                daily_usage[day_str] = {"cost":0,"requests":0,"input_tokens":0,"output_tokens":0}
            daily_usage[day_str]["cost"] += float(record.get("cost",0))
            daily_usage[day_str]["requests"] += int(record.get("n_requests",0))
            daily_usage[day_str]["input_tokens"] += int(record.get("prompt_tokens",0))
            daily_usage[day_str]["output_tokens"] += int(record.get("completion_tokens",0))

        total_cost = 0
        total_requests = 0
        total_tokens = 0
        for i in range(self.period):
            day_str = (today - timedelta(days=i)).isoformat()
            if day_str in daily_usage:
                total_cost += daily_usage[day_str]["cost"]
                total_requests += daily_usage[day_str]["requests"]
                total_tokens += daily_usage[day_str]["input_tokens"] + daily_usage[day_str]["output_tokens"]

        if total_tokens == 0:
            return 0

        if self.metric == "cost":
            # cost per token
            return round(total_cost / total_tokens, 6)
        if self.metric == "requests":
            return round(total_requests / total_tokens, 6)

class OpenAIExtraSensor(CoordinatorEntity, SensorEntity):
    """Extra global helper sensors."""
    def __init__(self, coordinator, name, entry_id):
        super().__init__(coordinator)
        self.name_key = name
        self.entry_id = entry_id
        self._attr_name = f"OpenAI {name.replace('_',' ').title()}"
        self._attr_unique_id = f"{entry_id}_{name}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self.entry_id}_all_models")},
            "name": "OpenAI All Models",
            "manufacturer": "OpenAI",
            "model": "Aggregate",
        }

    @property
    def native_unit_of_measurement(self):
        if self.name_key == "total_cost_all_time": return "$"
        if self.name_key == "requests_today": return "calls"
        if self.name_key == "efficiency_cost_per_1k_tokens_last_30_days": return "$/1k tokens"
        return None

    @property
    def native_value(self):
        data = self.coordinator.data
        today = date.today()
        daily_usage = {}
        for record in data:
            ts = record.get("aggregation_timestamp","" )
            if not ts:
                continue
            day_str = ts.split("T")[0]
            if day_str not in daily_usage:
                daily_usage[day_str] = {"cost":0,"requests":0,"input_tokens":0,"output_tokens":0}
            daily_usage[day_str]["cost"] += float(record.get("cost",0))
            daily_usage[day_str]["requests"] += int(record.get("n_requests",0))
            daily_usage[day_str]["input_tokens"] += int(record.get("prompt_tokens",0))
            daily_usage[day_str]["output_tokens"] += int(record.get("completion_tokens",0))

        if self.name_key == "total_cost_all_time":
            # Sum all days present in fetched window
            total = sum(v["cost"] for v in daily_usage.values())
            return round(total,4)

        if self.name_key == "requests_today":
            day_str = today.isoformat()
            return daily_usage.get(day_str, {}).get("requests", 0)

        if self.name_key == "efficiency_cost_per_1k_tokens_last_30_days":
            # Compute cost per 1k tokens over last 30 days
            total_cost = 0
            total_tokens = 0
            for i in range(30):
                day_str = (today - timedelta(days=i)).isoformat()
                if day_str in daily_usage:
                    total_cost += daily_usage[day_str]["cost"]
                    total_tokens += daily_usage[day_str]["input_tokens"] + daily_usage[day_str]["output_tokens"]
            if total_tokens == 0:
                return 0
            # $ per 1k tokens
            return round((total_cost / total_tokens) * 1000, 6)

        return 0
