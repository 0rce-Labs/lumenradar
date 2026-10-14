import numpy as np

from lumenradar.synth import Scene, burst_video, clean_video, periodic_video


def test_scene_frame_shapes_and_range():
    scene = Scene()
    f0 = scene.frame(0.0)
    f1 = scene.frame(1.0)
    assert f0.shape == (480, 640, 3)
    assert f0.dtype == np.uint8
    x, y = scene.light_center
    w, h = scene.light_size
    assert f1[y : y + h, x : x + w].mean() > f0[y : y + h, x : x + w].mean() + 100
    # background unchanged outside the light region (noise only)
    bg0 = f0.astype(int).copy()
    bg1 = f1.astype(int).copy()
    bg0[y : y + h, x : x + w] = 0
    bg1[y : y + h, x : x + w] = 0
    assert np.abs(bg0 - bg1).max() <= 10


def test_scene_reproducible():
    a = Scene(seed=1).frame(0.5)
    b = Scene(seed=1).frame(0.5)
    c = Scene(seed=2).frame(0.5)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_clean_video_is_flat():
    arr = clean_video(seconds=1.0, fps=30.0)
    assert arr.shape == (30, 480, 640, 3)
    means = arr.astype(np.float32).mean(axis=(1, 2, 3))
    assert means.std() < 0.5


def test_periodic_video_oscillates():
    arr = periodic_video(freq=2.0, seconds=2.0, fps=30.0, depth=0.8)
    means = Scene().light_means(arr)  # oracle: light region only
    x = means - means.mean()
    ac = np.correlate(x, x, mode="full")[len(x) - 1 :]
    lag = int(np.argmax(ac[5:])) + 5
    assert abs(lag - 15) <= 2  # 2 Hz @ 30 fps -> 15-frame period


def test_burst_video_has_pulses():
    pattern = (1, 1, 2, 1, 2, 1, 2)
    arr = burst_video(pattern=pattern, seconds=8.0, fps=30.0)
    means = Scene().light_means(arr)
    on = means > means.min() + 0.5 * (means.max() - means.min())
    rising = int(np.diff(on.astype(int)).clip(min=0).sum())
    assert rising == sum(pattern)  # 10 pulses
