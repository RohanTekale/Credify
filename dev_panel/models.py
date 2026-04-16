from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class QueryLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sql = models.TextField()
    exec_ms = models.IntegerField(default=0)
    row_count = models.IntegerField(default=0)
    success = models.BooleanField(default=True)
    error_msg = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.user}] {self.sql[:60]}"
    
class AuditLog(models.Model):
    LEVELS = [('INFO', 'INFO'), ('WARN', 'WARN'), ('ERROR', 'ERROR'), ('DEBUG', 'DEBUG'), ('SQL', 'SQL')]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    level = models.CharField(max_length=10, choices=LEVELS,default='INFO')
    message = models.TextField()
    meta = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.level}] {self.message[:60]}"