from threading import Thread

def Threaded(func):
    def threading_wrapper(*args, **kwargs):
        thread = Thread(target= func, args= args, kwargs= kwargs)
        thread.start()
        return thread
    return threading_wrapper