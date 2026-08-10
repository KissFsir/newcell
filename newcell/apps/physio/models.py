from django.db import models


class SerialConfig(models.Model):
    """生理串口配置（单例 id=1）：每台电脑端口号不同。"""
    enabled = models.BooleanField(default=False)
    port_a = models.CharField(max_length=64, default="COM6")  # 温湿度+脉搏板
    port_b = models.CharField(max_length=64, default="COM5")  # 皮电板
    baudrate = models.IntegerField(default=115200)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj


class PhysioSample(models.Model):
    """原始生理样本（每行一条，端口 A 填 temp/pulse/humidity，端口 B 填 gsr）。"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    port = models.CharField(max_length=1, default="a")  # a | b
    temp = models.FloatField(default=0.0)
    humidity = models.FloatField(default=0.0)
    pulse = models.FloatField(default=0.0)
    gsr = models.FloatField(default=0.0)

    class Meta:
        ordering = ["-timestamp"]


class PhysioRecord(models.Model):
    """每 5 秒一行生理信号聚合（脉搏波形/体表温度/皮肤湿度/皮电）。"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    hr_avg = models.FloatField(default=0.0)
    hr_min = models.FloatField(default=0.0)
    hr_max = models.FloatField(default=0.0)
    temp_avg = models.FloatField(default=0.0)
    skin_humidity_avg = models.FloatField(default=0.0)
    gsr_avg = models.FloatField(default=0.0)

    class Meta:
        ordering = ["-timestamp"]
