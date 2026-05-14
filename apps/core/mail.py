"""
SMTP email backend with debug-level logging of the full SMTP conversation.

smtplib writes debug output to sys.stderr via print(); this backend redirects
that stream to a logger so every SMTP command and response lands in the log file.
"""
import io
import logging
import sys

from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger('django.core.mail')


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


class DebugEmailBackend(EmailBackend):
    """Extends the standard SMTP backend to log the full SMTP conversation."""

    def open(self):
        result = super().open()
        if self.connection:
            # smtplib debug output goes to sys.stderr — redirect to logger
            self.connection.set_debuglevel(2)
            self.connection.debuglevel = 2
            self._smtp_stderr = sys.stderr
            sys.stderr = _LoggerWriter(lambda msg: logger.debug('SMTP | %s', msg))
        return result

    def close(self):
        if hasattr(self, '_smtp_stderr'):
            sys.stderr = self._smtp_stderr
            del self._smtp_stderr
        super().close()

    def send_messages(self, email_messages):
        logger.info(
            'Sending %d message(s) via %s:%s (user=%s)',
            len(email_messages),
            self.host,
            self.port,
            self.username,
        )
        for msg in email_messages:
            logger.debug(
                'Email | to=%s subject=%r from=%s',
                msg.to,
                msg.subject,
                msg.from_email,
            )
        try:
            count = super().send_messages(email_messages)
            logger.info('Email sent successfully (%d accepted)', count)
            return count
        except Exception as exc:
            logger.error('Email send failed: %s', exc, exc_info=True)
            raise
