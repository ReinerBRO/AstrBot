from watcher.event_source.models import AggregatedFeatures


class TriggerDetector:
    def __init__(self, min_clicks: int = 6, switch_trigger: bool = True):
        self.min_clicks = max(1, int(min_clicks))
        self.switch_trigger = bool(switch_trigger)

    def should_trigger(self, features: AggregatedFeatures) -> bool:
        if features.click_count >= self.min_clicks:
            return True
        if (
            self.switch_trigger
            and features.app_switch_count > 0
            and features.click_count > 0
        ):
            return True
        return False
