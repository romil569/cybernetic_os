from core.models import GestureName, GestureState, HandSnapshot, Landmark
from gestures.engine import GestureEngine, GestureEngineConfig


def hand_with(extended=(), pinch=False, velocity=(0.0, 0.0)):
    landmarks = [Landmark(0.5, 0.7) for _ in range(21)]
    landmarks[0], landmarks[9] = Landmark(0.5, 0.7), Landmark(0.5, 0.5)
    for index, (tip, pip) in enumerate(((8, 6), (12, 10), (16, 14), (20, 18))):
        landmarks[pip] = Landmark(0.5 + index * .03, .55)
        landmarks[tip] = Landmark(0.5 + index * .03, .25 if index in extended else .7)
    landmarks[3], landmarks[4] = Landmark(.35, .55), Landmark(.25, .55)
    if pinch:
        landmarks[4], landmarks[8] = Landmark(.45, .40), Landmark(.46, .40)
    return HandSnapshot(landmarks, "Right", 1.0, (.5, .55), {}, velocity)


def test_static_gesture_classification():
    engine = GestureEngine()
    assert engine.classify(hand_with(extended=(0, 1, 2, 3)))[0] == GestureName.OPEN_PALM
    assert engine.classify(hand_with())[0] == GestureName.FIST
    assert engine.classify(hand_with(extended=(0,)))[0] == GestureName.POINT
    assert engine.classify(hand_with(pinch=True))[0] == GestureName.PINCH


def test_pinch_temporal_transitions():
    engine = GestureEngine(GestureEngineConfig(smoothing_frames=1, cooldown_seconds=0))
    started = engine.update(hand_with(pinch=True), now=1.0)
    held = engine.update(hand_with(pinch=True), now=1.1)
    released = engine.update(None, now=1.2)
    assert started and started.state == GestureState.START
    assert held and held.state == GestureState.HOLD
    assert released and released.state == GestureState.RELEASE


def test_swipe_and_cooldown():
    engine = GestureEngine(GestureEngineConfig(smoothing_frames=1, cooldown_seconds=1.0, swipe_velocity=.5))
    first = engine.update(hand_with(extended=(0,), velocity=(1.0, 0.0)), now=10.0)
    engine.update(None, now=10.1)
    suppressed = engine.update(hand_with(extended=(0,), velocity=(1.0, 0.0)), now=10.4)
    assert first and first.gesture == GestureName.SWIPE_RIGHT
    assert suppressed is None
