from array import array
from math import sqrt


def int16_samples(pcm: bytes) -> array:
    samples = array("h")
    samples.frombytes(pcm)
    return samples


def rms_int16(pcm: bytes) -> float:
    samples = int16_samples(pcm)
    if not samples:
        return 0.0
    return sqrt(sum(sample * sample for sample in samples) / len(samples))
