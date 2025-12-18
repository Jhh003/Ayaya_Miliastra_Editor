# -*- coding: utf-8 -*-
"""
识别预热（连线前）。

职责：在视口 token 变化后，提前触发一次“截图 + 节点检测”，并将结果注入场景快照，
避免后续连接/配置步骤在同一视口中重复做昂贵识别。
"""


def prepare_for_connect_if_needed(executor, log_callback=None) -> None:
    if executor.should_prepare_for_connect():
        executor.prepare_for_connect(log_callback)
        executor.mark_connect_prepared()
        return
    executor.log("· 连线预热：视口未变化，跳过识别缓存刷新", log_callback)


