from __future__ import annotations
from datetime import date, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

SENSOR_PERIODS = [1, 7, 30, 90, 365]
METRICS = ["cost", "requests", "input_tokens", "output_tokens"]

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []
    data = coordinator.data

    models = {item["model"] for item in data}
    models.add("all_models")

    for model in models:
        for metric in METRICS:
            for period in SENSOR_PERIODS:
                sensors.append(OpenAISensor(coordinator, model, metric, period, entry.entry_id))
            if metric in ["cost", "requests"]:
                for period in SENSOR_PERIODS:
                    sensors.append(OpenAIEfficiencySensor(coordinator, model, metric, period, entry.entry_id))

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
        if "tokens" in self.metric: return "tokens"
        if "cost" in self.metric: return "$"
        if "requests" in self.metric: return "calls"
        return None

    @property
    def native_value(self):
        data = self.coordinator.data
        model_data = data if self.model=="all_models" else [d for d in data if d["model"]==self.model]
        if not model_data: return 0

        today = date.today()
        daily_usage = {}
        for record in model_data:
            ts = record.get("aggregation_timestamp","")
            if not ts: continue
            day_str = ts.split("T")[0]
            if day_str not in daily_usage:
                daily_usage[day_str] = {"cost":0,"requests":0,"input_tokens":0,"output_tokens":0}
            daily_usage[day_str]["cost"] += float(record.get("cost",0))
            daily_usage[day_str]["requests"] += int(record.get("n_requests",0))
            daily_usage[day_str]["input_tokens"] += int(record.get("prompt_tokens",0))
            daily_usage[day_str]["output_tokens"] += int(record.get("completion_tokens",0))

        total = sum(daily_usage.get((today - timedelta(days=i)).isoformat(), {}).get(self.metric,0) for i in range(self.period))
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
        return "$/token" if self.metric=="cost" else "requests/token"

    @property
    def native_value(self):
        data = self.coordinator.data
        model_data = data if self.model=="all_models" else [d for d in data if d["model"]==self.model]
        if not model_data: return 0

        today = date.today()
        daily_usage = {}
        for record in model_data:
            ts = record.get("aggregation_timestamp","")
            if not ts: continue
            day_str = ts.split("T")[0]
            if day_str not in daily_usage:
                daily_usage[day_str] = {"cost":0,"requests":0,"input_tokens":0,"output_tokens":0}
            daily_usage[day_str]["cost"] += float(record.get("cost",0))
            daily_usage[day_str]["requests"] += int(record.get("n_requests",0))
            daily_usage[day_str]["input_tokens"] += int(record.get("prompt_tokens",0))
            daily_usage[day_str]["output_tokens"] += int(record.get("completion_tokens",0))

        total_cost = sum(daily_usage.get((today - timedelta(days=i)).isoformat(), {}).get("cost",0) for i in range(self.period))
        total_requests = sum(daily_usage.get((today - timedelta(days=i)).isoformat(), {}).get("requests",0) for i in range(self.period))
        total_tokens = sum(daily_usage.get((today - timedelta(days=i)).isoformat(), {}).get("input_tokens",0) + 
                           daily_usage.get((today - timedelta(days=i)).isoformat(), {}).get("output_tokens",0)
                           for i in range(self.period))
        if total_tokens == 0: return 0
        return round(total_cost/total_tokens,6) if self.metric=="cost" else round(total_requests/total_tokens,6)
