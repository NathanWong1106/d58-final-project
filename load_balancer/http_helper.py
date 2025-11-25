class HTTPResponse:
    def __init__(self, status_code: int, body: str, headers: dict):
        self.status_code = status_code
        self.body = body
        self.headers = headers

    def get_response_string(self) -> str:
        response_lines = [f"HTTP/1.1 {self.status_code} {self._get_status_message()}"]
        for header, value in self.headers.items():
            response_lines.append(f"{header}: {value}")
        response_lines.append("")  # Blank line between headers and body
        response_lines.append(self.body)
        return "\r\n".join(response_lines)
    
    def _get_status_message(self) -> str:
        status_messages = {
            200: "OK",
            500: "Internal Server Error",
            503: "Service Unavailable",
        }
        return status_messages.get(self.status_code, "Unknown Status")