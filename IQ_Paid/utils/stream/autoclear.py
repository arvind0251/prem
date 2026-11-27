import os
from config import autoclean
from IQ_Paid.utils.songcache import is_cache_path


async def auto_clean(popped):
    try:
        rem = popped["file"]
        autoclean.remove(rem)
        if is_cache_path(rem):  # saved songs stay on the VPS
            return
        count = autoclean.count(rem)
        if count == 0:
            if "vid_" not in rem or "live_" not in rem or "index_" not in rem:
                try:
                    os.remove(rem)
                except:
                    pass
    except:
        pass

