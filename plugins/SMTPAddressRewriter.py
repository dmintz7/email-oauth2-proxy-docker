import re
import enum
import plugins.BasePlugin

SMTP_MAIL_FROM_MATCHER = re.compile(b'MAIL FROM:<(.+?)>\r\n', re.IGNORECASE)
SMTP_RCPT_TO_MATCHER = re.compile(b'RCPT TO:.+\r\n', re.IGNORECASE)


class SMTPAddressRewriter(plugins.BasePlugin.BasePlugin):
    class STATE(enum.Enum):
        NONE = 1
        MAIL_FROM = 2
        RCPT_TO = 3
        DATA = 4

    def __init__(self, static_sender=None, reply_to=None):
        super().__init__()
        self.static_sender = static_sender.encode('utf-8') if static_sender else None
        self.reply_to = reply_to.encode('utf-8') if reply_to else None
        self.original_sender = None
        self.sending_state, self.previous_line_ended, self.matched_addresses = self.reset()

    def reset(self):
        self.sending_state = self.STATE.NONE
        self.previous_line_ended = False
        self.matched_addresses = []
        self.original_sender = None
        return self.sending_state, self.previous_line_ended, self.matched_addresses

    def receive_from_client(self, byte_data):
        if self.sending_state == self.STATE.NONE:
            if SMTP_MAIL_FROM_MATCHER.match(byte_data):
                self.sending_state = self.STATE.MAIL_FROM
                return self.replace_mail_from(byte_data)
            return byte_data

        if len(byte_data) == 6 and byte_data.lower() == b'rset\r\n':
            self.reset()

        elif self.sending_state == self.STATE.MAIL_FROM:
            if SMTP_RCPT_TO_MATCHER.match(byte_data):
                self.sending_state = self.STATE.RCPT_TO

        elif self.sending_state == self.STATE.RCPT_TO:
            if not SMTP_RCPT_TO_MATCHER.match(byte_data) and byte_data.lower() == b'data\r\n':
                self.sending_state = self.STATE.DATA

        elif self.sending_state == self.STATE.DATA:
            if not byte_data.upper().startswith(b'QUIT'):
                byte_data = self.replace_from_header(byte_data)

        return byte_data

    def replace_mail_from(self, byte_data):
        match = SMTP_MAIL_FROM_MATCHER.match(byte_data)
        if match:
            self.original_sender = match.group(1)
            if self.static_sender:
                byte_data = b'MAIL FROM:<%b>\r\n' % self.static_sender
        return byte_data

    def replace_from_header(self, byte_data):
        if not self.static_sender or not self.original_sender:
            return byte_data

        from_pattern = re.compile(br'^From: .*\r\n', re.IGNORECASE | re.MULTILINE)
        reply_to_pattern = re.compile(br'^Reply-To: .*\r\n', re.IGNORECASE | re.MULTILINE)

        new_from = b'From: "' + self.original_sender + b'" <' + self.static_sender + b'>\r\n'
        new_reply_to = b'Reply-To: <' + self.reply_to + b'>\r\n' if self.reply_to else b''

        if from_pattern.search(byte_data):
            byte_data = from_pattern.sub(new_from, byte_data, 1)
            if self.reply_to and not reply_to_pattern.search(byte_data):
                byte_data = byte_data.replace(new_from, new_from + new_reply_to, 1)
        else:
            insertion = new_from + new_reply_to
            byte_data = byte_data.replace(b'\r\n', insertion + b'\r\n', 1)

        return byte_data

    def receive_from_server(self, byte_data):
        return byte_data
