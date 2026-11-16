import multiprocessing

bind = "127.0.0.1:8000"          # only Nginx can reach it
workers = max(2, multiprocessing.cpu_count() * 2 + 1)
timeout = 30
accesslog = "-"
errorlog = "-"
