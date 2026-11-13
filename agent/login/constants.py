SERVER_1000_LIST_ROI = [432, 277, 447, 250]

SERVER_TAB_BOXES = {
    "public": {
        ">=1000": [437, 262, 54, 13],
        "<1000": [502, 263, 50, 11],
    },
    "non_wipe": {
        ">=601": [565, 263, 48, 11],
        "<601": [634, 263, 36, 11],
    },
    "alliance": {
        "all": [688, 263, 52, 12],
    },
}

SERVER_GRID_COLUMNS = 4
SERVER_VISIBLE_ROWS = 13
# 目标行落在可见区的第 7 行，给首次估算留出上下各约 6 行的误差。
SERVER_AIM_ROW = 6
# 滑块上沿的最小 y 与下沿的最大 y；拖动终点超出窗口时 Swipe 会失败，所以必须夹在轨道内。
SERVER_THUMB_TRACK = (290, 518)
# 总拖动次数上限，只防死循环。
SERVER_SCROLL_MAX_DRAGS = 5
