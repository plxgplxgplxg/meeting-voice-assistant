ALLOWED_AUDIO_EXTENSIONS = frozenset(
    {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".webm", ".mp4"}
)


def looks_like_audio_container(head: bytes) -> bool:
    """Check the leading bytes of a file against known audio/video containers.

    This is a cheap content sniff that rejects files whose extension was
    simply renamed. A deeper probe with ffprobe happens during processing.

    Args:
        head: First bytes of the uploaded file (at least 16 recommended).

    Returns:
        True when the bytes match WAV, MP3, AAC (ADTS), FLAC, Ogg, MP4/M4A or WebM/Matroska.
    """
    if len(head) < 4:
        return False
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return True
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return True
    if head[:2] in (b"\xff\xf1", b"\xff\xf9"):
        return True
    if head[:4] in (b"fLaC", b"OggS", b"\x1a\x45\xdf\xa3"):
        return True
    return head[4:8] == b"ftyp"
