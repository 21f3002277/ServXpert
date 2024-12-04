from celery import Celery
from flask import current_app as app

celery = Celery("Backend Jobs")

celery.conf.update(
    timezone='Asia/Kolkata',
    enable_utc=False,  # Disable UTC if you prefer working with local time
    broker_connection_retry_on_startup=True,
)


class BackendContextTask(celery.Task):

    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)