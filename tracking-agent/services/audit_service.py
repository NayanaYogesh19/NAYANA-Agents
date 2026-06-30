import multiprocessing

from services.audit_worker import _run_full_audit


def run_tracking_audit(website_url, industry_type):

    result_queue = multiprocessing.Queue()

    process = multiprocessing.Process(
        target=_run_full_audit,
        args=(website_url, industry_type, result_queue)
    )

    process.start()
    process.join(timeout=120)

    if not result_queue.empty():
        return result_queue.get()

    return None
