"""UTF-8 stdio configuration for cross-platform CLI compatibility."""
import io
import sys


def _reconfigure_stream(stream):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        try:
            wrapped = io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace")
            return wrapped
        except (AttributeError, OSError, ValueError):
            pass
    return stream


def configure_utf8_stdio():
    """Configure stdout and stderr to use UTF-8 encoding (for Windows non-UTF-8 locales)."""
    sys.stdout = _reconfigure_stream(sys.stdout)
    sys.stderr = _reconfigure_stream(sys.stderr)
