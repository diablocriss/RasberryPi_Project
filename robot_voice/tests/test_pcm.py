from audio.pcm import pcm_to_array


def test_pcm_to_array_reads_int16_samples():
    samples = pcm_to_array((1).to_bytes(2, "little", signed=True) + (-2).to_bytes(2, "little", signed=True))

    assert list(samples) == [1, -2]
