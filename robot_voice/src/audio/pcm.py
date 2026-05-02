from array import array


def pcm_to_array(data: bytes):
    try:
        import numpy as np
    except ImportError:
        samples = array("h")
        samples.frombytes(data)
        return samples

    return np.frombuffer(data, dtype=np.int16)
