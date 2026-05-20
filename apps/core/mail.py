"""
SMTP email backends.

LoggingEmailBackend  — default production backend.  Logs send attempts and
                       errors at INFO/ERROR level.  No SMTP protocol tracing.

DebugEmailBackend    — development/diagnostic opt-in (SMTP_DEBUG=1).  Enables
                       smtplib debug level 2 and captures the full SMTP
                       conversation via the django.core.mail logger.
                       Do NOT use in production: AUTH exchanges and message
                       content will appear in logs.
"""
import io
import logging
import sys

from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger('django.core.mail')


class LoggingEmailBackend(EmailBackend):
    """Standard SMTP backend with high-level send/error logging only."""

    def send_messages(self, email_messages):
        logger.info(
            'Sending %d message(s) via %s:%s',
            len(email_messages),
            self.host,
            self.port,
        )
        try:
            count = super().send_messages(email_messages)
            logger.info('Email sent successfully (%d accepted)', count)
            return count
        except Exception as exc:
            logger.error('Email send failed: %s', exc, exc_info=True)
            raise


class _LoggerWriter(io.RawIOBase):
    """File-like object that forwards writes to a logger."""

    def __init__(self, log_fn):
        self._log = log_fn
        self._buf = ''

    def write(self, s):
        self._buf += s if isinstance(s, str) else s.decode('utf-8', errors='replace')
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            line = line.rstrip('\r')
            if line:
                self._log(line)
        return len(s)

    def readable(self):
        return False

    def writable(self):
        return True


class DebugEmailBackend(LoggingEmailBackend):
    """
    Extends LoggingEmailBackend with full SMTP protocol tracing.

    Opt-in only — set SMTP_DEBUG=1 in the environment.
    Redirects global sys.stderr while the SMTP connection is open, which
    captures smtplib's debug output into the django.core.mail logger.
    """

    def open(self):
        result = super().open()
        if self.connection:
            self.connection.set_debuglevel(2)
            self._smtp_stderr = sys.stderr
            sys.stderr = _LoggerWriter(lambda msg: logger.debug('SMTP | %s', msg))
        return result

    def close(self):
        if hasattr(self, '_smtp_stderr'):
            sys.stderr = self._smtp_stderr
            del self._smtp_stderr
        super().close()
