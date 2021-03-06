# -*- encoding: utf-8 -*-

"""
------------------------------------------
@File       : worker_queue_utils.py
@Author     : maixiaochai
@Email      : maixiaochai@outlook.com
@CreatedOn  : 2021/6/17 10:32
------------------------------------------
原作者代码：https://github.com/bslatkin/effectivepython/blob/master/example_code/item_55.py
"""
from queue import Queue
from threading import Thread

from settings import cfg


class CloseableQueue(Queue):
    """
        比较高级的队列用法
        Tips:
            Queue.get()会持续阻塞，直到队列中 put数据才返回
    """
    SENTINEL = object()

    def close(self):
        self.put(self.SENTINEL)

    def __iter__(self):
        while True:
            # 因为queue.get会持续阻塞，所以，在流程中并不会造成CPU时间的浪费
            item = self.get()
            try:
                if item is self.SENTINEL:
                    return  # 让线程退出

                yield item

            finally:
                self.task_done()


class StoppableWorker(Thread):
    """
        比较高级的 Worker
    """

    def __init__(self, func, in_queue, out_queue=None):
        super().__init__()
        self.func = func
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.debug_display = cfg.queue_size_display

    def judge_queue_name(self):
        func_name = self.func.__name__
        q_name1 = ''
        q_name2 = ''

        if func_name == 'url_parse':
            q_name1 = 'url_queue'
            q_name2 = 'video_obj_queue'

        elif func_name == 'video_check':
            q_name1 = 'video_obj_queue'
            q_name2 = 'video_save_queue'

        elif func_name == 'video_save':
            q_name1 = 'video_save_queue'

        return func_name, q_name1, q_name2

    def run(self):
        func_name, name1, name2 = self.judge_queue_name() if cfg.queue_size_display else ('', '', '')

        for item in self.in_queue:
            if self.debug_display:
                print(f"func: {func_name}, running")

            result = self.func(item)

            # 当有内容返回的时候，才放到下一个队列
            # 这里主要是处理done_queue, 不向其中添加任何内容，节省空间
            if self.out_queue and result:
                self.out_queue.put(result)

            if self.debug_display:
                info = f"func: {func_name} | {name1}: {self.in_queue.qsize()} | {name2}: {self.out_queue.qsize()}, done."
                print(info)


def start_threads(count, *args):
    threads = [StoppableWorker(*args) for _ in range(count)]
    for thread in threads:
        thread.start()

    return threads


def stop_thread(closable_queue, threads):
    for _ in threads:
        closable_queue.close()

    # 实际上意味着等到队列为空，再执行别的操作
    closable_queue.join()

    # 等待所有线程结束再退出
    for thread in threads:
        thread.join()
