import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import calc_player_points  # noqa: E402


def _p(**kw):
    base = dict(goals=0, assists=0, clean_sheets=0, yellow_cards=0,
                red_cards=0, saves=0, position="MID", nation="Nowhere")
    base.update(kw)
    return base


def test_gk_goal_worth_6():
    assert calc_player_points(_p(position="GK", goals=1), "France")["points"] == 6.0


def test_fwd_goal_worth_4():
    assert calc_player_points(_p(position="FWD", goals=1), "France")["points"] == 4.0


def test_mid_goal_worth_5():
    assert calc_player_points(_p(position="MID", goals=1), "France")["points"] == 5.0


def test_assist_worth_3():
    assert calc_player_points(_p(assists=2), "France")["points"] == 6.0


def test_backed_nation_multiplier():
    # FWD goal = 4, x1.5 = 6
    assert calc_player_points(_p(position="FWD", goals=1, nation="Brazil"),
                              "Brazil")["points"] == 6.0


def test_saves_threshold():
    # 6 saves -> floor(6/3)=2 pts
    assert calc_player_points(_p(position="GK", saves=6), "")["points"] == 2.0
    # 5 saves -> floor(5/3)=1 pt
    assert calc_player_points(_p(position="GK", saves=5), "")["points"] == 1.0


def test_yellow_and_red_cards():
    assert calc_player_points(_p(yellow_cards=1), "")["points"] == -1.0
    assert calc_player_points(_p(red_cards=1), "")["points"] == -3.0


def test_clean_sheet_def_vs_mid():
    assert calc_player_points(_p(position="DEF", clean_sheets=1), "")["points"] == 4.0
    assert calc_player_points(_p(position="MID", clean_sheets=1), "")["points"] == 1.0
    # FWD clean sheet worth nothing
    assert calc_player_points(_p(position="FWD", clean_sheets=1), "")["points"] == 0.0


def test_combined_with_multiplier():
    # DEF, 1 goal(6) + 1 assist(3) + 1 CS(4) = 13, x1.5 = 19.5
    p = _p(position="DEF", goals=1, assists=1, clean_sheets=1, nation="Spain")
    assert calc_player_points(p, "Spain")["points"] == 19.5


def _run():
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for f in funcs:
        try:
            f()
            print(f"PASS  {f.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {f.__name__}: {e}")
    print(f"\n{len(funcs)-failed}/{len(funcs)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run() else 0)
