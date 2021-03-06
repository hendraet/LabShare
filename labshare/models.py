import pytz

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class Device(models.Model):
    name = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()

    class Meta:
        permissions = (
            ('use_device', 'User/Group is allowed to use that device'),
        )

    def __str__(self):
        return self.name

    def can_be_used_by(self, user):
        content_type = ContentType.objects.get_for_model(self)
        permission_name = "{app}.use_{model}".format(app=content_type.app_label, model=content_type.model)
        return user.has_perm(permission_name, self) or user.has_perm(permission_name)

    def serialize(self):
        return {
            'name': self.name,
            'gpus': [gpu.serialize() for gpu in self.gpus.all()]
        }


class GPU(models.Model):
    uuid = models.CharField(unique=True, max_length=255)
    device = models.ForeignKey(Device, related_name="gpus", on_delete=models.CASCADE)
    last_updated = models.DateTimeField(auto_now=True)
    model_name = models.CharField(max_length=255)
    used_memory = models.CharField(max_length=100)
    total_memory = models.CharField(max_length=100)
    in_use = models.BooleanField(default=False)
    marked_as_failed = models.BooleanField(default=False)

    def __str__(self):
        return self.model_name

    def last_update_too_long_ago(self):
        return self.last_updated < timezone.now() - timedelta(minutes=30)

    def current_reservation(self):
        try:
            return self.reservations.earliest("time_reserved")
        except Reservation.DoesNotExist as e:
            return None

    def last_reservation(self):
        try:
            return self.reservations.latest("time_reserved")
        except Reservation.DoesNotExist as e:
            return None

    def get_next_reservations(self):
        reservations = self.reservations.all()
        if self.reservations.count() <= 1:
            return []
        return reservations.order_by("time_reserved").all()[1:]

    def get_current_reservation(self):
        if self.reservations.count() == 0:
            return None
        return self.current_reservation()

    def get_current_user(self):
        return getattr(self.get_current_reservation(), 'user', None)

    def get_next_users(self):
        return [getattr(reservation, 'user', '') for reservation in self.get_next_reservations()]

    def memory_usage(self):
        return "{used} / {total}".format(used=self.used_memory, total=self.total_memory)

    def serialize(self):
        extension_possible = False
        if self.get_current_reservation() is not None:
            extension_possible = self.get_current_reservation().is_extension_possible()
        return {
            'name': self.model_name,
            'uuid': self.uuid,
            'memory': self.memory_usage(),
            'processes': [process.serialize() for process in self.processes.all()],
            'last_update': self.last_updated.astimezone(pytz.timezone(settings.TIME_ZONE)).isoformat(),
            'failed': self.marked_as_failed,
            'in_use': self.in_use,
            'current_user': getattr(self.get_current_user(), 'username', ''),
            'extension_possible': extension_possible,
            'next_users': [getattr(user, 'username', '') for user in self.get_next_users()]
        }


class GPUProcess(models.Model):
    gpu = models.ForeignKey(GPU, related_name="processes", on_delete=models.CASCADE)
    name = models.CharField(max_length=511, blank=True)
    pid = models.PositiveIntegerField()
    memory_usage = models.CharField(max_length=100, blank=True)
    username = models.CharField(max_length=250, blank=True)

    def __str__(self):
        return "{process} (by {username}) running on {gpu} (using {memory})".format(
            process=self.name,
            username=self.username,
            gpu=self.gpu,
            memory=self.memory_usage,
        )

    def serialize(self):
        return {
            'name': self.name,
            'pid': self.pid,
            'memory_usage': self.memory_usage,
            'username': self.username,
        }


class Reservation(models.Model):
    gpu = models.ForeignKey(GPU, related_name="reservations", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="reservations", on_delete=models.CASCADE)
    time_reserved = models.DateTimeField(auto_now_add=True)
    usage_started = models.DateTimeField(null=True, blank=True)
    usage_expires = models.DateTimeField(null=True, blank=True)
    extension_reminder_sent = models.BooleanField(default=False)
    user_reserved_next_available_spot = models.BooleanField(default=False)

    def __str__(self):
        return "{gpu} on {device}, {user}".format(device=self.gpu.device, gpu=self.gpu, user=self.user)

    @staticmethod
    def usage_period():
        return timedelta(days=8)

    @staticmethod
    def reminder_period():
        return timedelta(hours=48)

    def start_usage(self, save=True):
        self.usage_started = timezone.now()
        self.usage_expires = timezone.now() + self.usage_period()
        if save:
            self.save(update_fields=["usage_started", "usage_expires"])

    def needs_reminder(self):
        if self.extension_reminder_sent:
            return False
        return self.is_extension_possible()

    def is_extension_possible(self):
        if self.usage_started is None:
            return False
        return timezone.now() + self.reminder_period() > self.usage_expires

    def is_usage_expired(self):
        if self.usage_expires is None:
            return False
        return timezone.now() > self.usage_expires

    def extend(self):
        if not self.is_extension_possible():
            return False
        self.usage_expires = timezone.now() + self.usage_period()
        self.extension_reminder_sent = False
        self.save(update_fields=["usage_expires", "extension_reminder_sent"])
        return True

    def set_reminder_sent(self):
        self.extension_reminder_sent = True
        self.save(update_fields=["extension_reminder_sent"])


class EmailAddress(models.Model):
    user = models.ForeignKey(User, related_name="email_addresses", on_delete=models.CASCADE)
    email = models.EmailField(max_length=255)

    def __str__(self):
        return "{}: {}".format(self.user, self.email)
