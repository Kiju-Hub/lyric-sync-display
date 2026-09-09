"""Windows Now Playing (GSMTC) 조회."""

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)


async def get_now_playing():
    """현재 재생 세션 정보를 dict로 반환. 재생 중인 세션이 없으면 None."""
    manager = await MediaManager.request_async()
    session = manager.get_current_session()
    if session is None:
        return None

    info = await session.try_get_media_properties_async()
    if not info.title:
        return None

    timeline = session.get_timeline_properties()
    playback_info = session.get_playback_info()

    return {
        "title": info.title,
        "artist": info.artist,
        "position": timeline.position.total_seconds(),
        "duration": timeline.end_time.total_seconds(),
        "status": playback_info.playback_status.name,  # PLAYING / PAUSED / STOPPED 등
    }
