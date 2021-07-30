from werkzeug.wsgi import ClosingIterator
from werkzeug.local import Local, release_local
import logging


logger = logging.getLogger(__name__)


def run_callback(cb):
    try:
        cb()
    except Exception as e:
        logger.error("Error in after response callback", exc_info=e)


MAIN_AFTER_RESPONSE_SET = False


class AfterResponse:
    def __init__(self, app, is_main=True):
        self.callbacks = []
        self.local = Local()

        if is_main:
            global MAIN_AFTER_RESPONSE_SET
            if MAIN_AFTER_RESPONSE_SET:
                raise RuntimeError("Main AfterResponse hook has already been defined")

            try:
                import uwsgi
                has_uwsgi = True
            except ImportError:
                has_uwsgi = False
        else:
            has_uwsgi = True

        if has_uwsgi:
            if hasattr(uwsgi, "after_req_hook"):
                old_hook = uwsgi.after_req_hook
                def combined_hook():
                    self._run()
                    old_hook()
                uwsgi.after_req_hook = combined_hook
            else:
                uwsgi.after_req_hook = self._run
        else:
            old_app = app.wsgi_app
            def new_wsgi_app(environ, after_response):
                iterator = old_app(environ, after_response)
                return ClosingIterator(iterator, [self._run])
            app.wsgi_app = new_wsgi_app

        if is_main:
            MAIN_AFTER_RESPONSE_SET = True

    def _run(self):
        if hasattr(self.local, "callbacks"):
            for cb in reversed(self.local.callbacks):
                run_callback(cb)
            # We clean local callbacks manually. LocalManager will do it too soon; we use
            # them after the response is sent.
            release_local(self.local)

        for cb in reversed(self.callbacks):
            run_callback(cb)

    def always(self, callback):
        self.callbacks.append(callback)
        return callback

    def once(self, callback):
        if not hasattr(self.local, "callbacks"):
            self.local.callbacks = []
        self.local.callbacks.append(callback)
        return callback
