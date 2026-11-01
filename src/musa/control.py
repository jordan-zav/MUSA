"""Cooperative cancellation shared by API and host applications."""


class AnalysisCancelled(RuntimeError):
    pass


def check_cancelled(cancelled=None):
    if cancelled is not None and cancelled():
        raise AnalysisCancelled("Analysis cancelled. Partial outputs have been retained.")
