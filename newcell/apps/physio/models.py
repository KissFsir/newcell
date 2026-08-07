from django.db import models


class PhysioRecord(models.Model):
    """每 5 秒一行生理信号聚合（心率/体表温度/皮肤湿度）。"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    hr_avg = models.FloatField(default=0.0)
    hr_min = models.FloatField(default=0.0)
    hr_max = models.FloatField(default=0.0)
    temp_avg = models.FloatField(default=0.0)
    skin_humidity_avg = models.FloatField(default=0.0)

    class Meta:
        ordering = ["-timestamp"]
