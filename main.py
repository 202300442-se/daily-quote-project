"""한국 날짜에 맞는 문구를 골라 하나의 HTML 파일로 만듭니다. 외부 패키지 불필요."""

import argparse
from datetime import date, datetime, timedelta
from html import escape
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
QUOTES_FILE = Path(__file__).with_name("quotes.json")


def load_quotes(filepath=QUOTES_FILE):
    """비어 있거나 형식이 잘못된 문구 목록은 출력 파일을 만들기 전에 중단합니다."""
    with Path(filepath).open(encoding="utf-8") as source:
        quotes = json.load(source)
    if not isinstance(quotes, list) or not quotes:
        raise ValueError("quotes.json은 문구가 한 개 이상 있는 배열이어야 합니다.")
    for number, item in enumerate(quotes, 1):
        if not isinstance(item, dict):
            raise ValueError(f"{number}번째 문구는 객체여야 합니다.")
        for key in ("quote", "author"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"{number}번째 문구의 {key}는 비어 있지 않은 문자열이어야 합니다.")
        if "topic" in item and not isinstance(item["topic"], str):
            raise ValueError(f"{number}번째 문구의 topic은 문자열이어야 합니다.")
    return quotes


def parse_preview_date(value):
    """입력은 정확히 YYYY-MM-DD 형식으로 받고 존재하는 날짜인지 확인합니다."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise argparse.ArgumentTypeError("날짜는 YYYY-MM-DD 형식으로 입력하세요.")
    try:
        result = date.fromisoformat(value)
        if result == date.min:
            raise ValueError("어제 날짜를 계산할 수 없습니다.")
        return result
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"사용할 수 없는 날짜입니다: {value}") from error


def choose_date(preview_date, generated_at):
    """생성 시각이 UTC여도 날짜 선택은 한국시간으로 합니다."""
    return preview_date if preview_date is not None else generated_at.astimezone(KST).date()


def pick_quote(quotes, target_date):
    """날짜 순번으로 목록을 순환합니다. 같은 날짜와 같은 목록이면 같은 항목입니다."""
    return quotes[(target_date.toordinal() - 1) % len(quotes)]


def generate_html(quotes, target_date, generated_at, is_preview=False, environment=None):
    """사용자가 추가한 문구와 메타데이터를 HTML 이스케이프하여 화면을 만듭니다."""
    environment = os.environ if environment is None else environment
    yesterday = target_date - timedelta(days=1)
    today_quote = pick_quote(quotes, target_date)
    yesterday_quote = pick_quote(quotes, yesterday)
    generated_kst = generated_at.astimezone(KST)
    mode_label = "날짜 미리보기" if is_preview else "한국 날짜 기준"
    previous_label = "선택한 날짜의 전날" if is_preview else "어제의 한 문장"
    run_number = environment.get("GITHUB_RUN_NUMBER", "")
    run_attempt = environment.get("GITHUB_RUN_ATTEMPT", "1")
    commit = environment.get("GITHUB_SHA", "")
    provenance = []
    if run_number:
        provenance.append(f"Actions 실행 #{escape(run_number)} · 시도 {escape(run_attempt)}")
    if commit:
        provenance.append(f"커밋 {escape(commit[:7])}")
    provenance_text = " · ".join(provenance) if provenance else "로컬 생성본"
    preview_note = '<p class="preview-note">선택한 날짜의 문구를 확인하는 화면입니다.</p>' if is_preview else ""
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="날짜에 따라 골라 보는 학습과 협업의 한 문장">
  <title>오늘의 한 문장</title>
  <style>
    * {{ box-sizing: border-box; }}
    :root {{ color-scheme: light; --green: #183f35; --ivory: #f5f2e9; --muted: #62736a; }}
    body {{ margin: 0; background: var(--ivory); color: var(--green); font-family: -apple-system, BlinkMacSystemFont, "Malgun Gothic", sans-serif; padding: 48px 28px 28px; }}
    .container {{ max-width: 1040px; margin: auto; }}
    .eyebrow {{ margin: 0 0 22px; padding-bottom: 22px; border-bottom: 1px solid #183f3530; font-size: 10px; font-weight: 700; letter-spacing: .25em; }}
    h1 {{ font-family: "AppleMyungjo", "Batang", Georgia, serif; font-size: clamp(32px,5vw,48px); font-weight: 400; letter-spacing: -.05em; margin: 32px 0 12px; }}
    .intro {{ font-size: 14px; line-height: 1.8; color: var(--muted); margin: 0 0 28px; }}
    .date-badge {{ display: flex; align-items: center; gap: 14px; margin-bottom: 22px; font-size: 12px; letter-spacing: .05em; }}
    .mode {{ color: var(--muted); padding-left: 14px; border-left: 1px solid #183f3530; }}
    .preview-note {{ border-left: 2px solid #a68a51; padding: 10px 16px; font-size: 13px; }}
    .quote-card {{ position: relative; overflow: hidden; background: var(--green); color: var(--ivory); border-radius: 4px 64px 4px 4px; padding: 48px 70px 42px; text-align: center; box-shadow: 0 18px 40px #183f3510; }}
    .quote-card::after {{ content: ""; width: 220px; height: 220px; border: 1px solid #f5f2e914; border-radius: 50%; position: absolute; right: -120px; bottom: -100px; pointer-events: none; }}
    .quote-mark {{ display: block; font: 76px/.8 Georgia,serif; color: #c2bf9e; margin: 0 0 16px; }}
    .quote-text {{ position: relative; font-family: "AppleMyungjo", "Batang", Georgia,serif; font-size: clamp(25px,3.5vw,38px); font-weight: 400; line-height: 1.8; word-break: keep-all; overflow-wrap: anywhere; max-width: 730px; margin: 0 auto 26px; letter-spacing: -.035em; }}
    .divider {{ width: 30px; height: 1px; background: #c2bf9e; margin: 0 auto 20px; }}
    .author {{ font-size: 13px; color: #e1e4d7; margin: 0 0 10px; }}
    .topic {{ display: inline-block; font-size: 11px; color: #d3dbca; border: 1px solid #f5f2e930; padding: 5px 12px; border-radius: 20px; margin: 0; }}
    .yesterday {{ display: grid; grid-template-columns: 210px 1fr; column-gap: 30px; padding: 30px 0; margin: 24px 0 14px; border-top: 1px solid #183f3530; border-bottom: 1px solid #183f3530; }}
    .yesterday-label {{ grid-row: span 2; font-size: 11px; line-height: 1.8; color: var(--muted); margin: 0; }}
    .yesterday-quote {{ font-family: "AppleMyungjo", "Batang", Georgia, serif; font-size: 19px; line-height: 1.8; word-break: keep-all; overflow-wrap: anywhere; margin: 0; }}
    .yesterday-author {{ font-size: 11px; color: var(--muted); margin: 10px 0 0; }}
    footer {{ display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px 24px; padding-top: 12px; font-size: 10px; line-height: 1.9; color: var(--muted); }}
    footer p {{ margin: 0; }}
    footer details {{ width: 100%; }}
    summary {{ cursor: pointer; width: fit-content; padding: 5px 0; }}
    summary:focus-visible {{ outline: 2px solid var(--green); outline-offset: 4px; }}
    @media(max-width:600px) {{ body {{ padding: 28px 20px 22px; }} h1 {{ margin-top: 26px; }} .quote-card {{ padding: 38px 25px 34px; border-top-right-radius: 44px; }} .yesterday {{ grid-template-columns: 1fr; gap: 12px; padding: 24px 0; }} .yesterday-label {{ grid-row: auto; }} .yesterday-quote {{ font-size: 17px; }} .yesterday-author {{ margin: 0; }} footer {{ display: block; }} footer p {{ margin-bottom: 5px; }} }}
  </style>
</head>
<body>
  <main class="container">
    <p class="eyebrow">TODAY IN ONE SENTENCE</p>
    <h1>오늘의 한 문장</h1>
    <p class="intro">잠시 머물러, 오늘의 문장을 마음에 담아보세요.</p>
    <div class="date-badge"><time id="selected-date" datetime="{target_date.isoformat()}">{target_date.isoformat()}</time><span class="mode">{mode_label}</span></div>
    {preview_note}
    <section class="quote-card" aria-label="선택한 날짜의 문구">
      <span class="quote-mark" aria-hidden="true">“</span>
      <p class="quote-text" id="today-quote">{escape(today_quote['quote'])}</p>
      <div class="divider" aria-hidden="true"></div>
      <p class="author">— {escape(today_quote['author'])}</p>
      <p class="topic">{escape(today_quote.get('topic', ''))}</p>
    </section>
    <section class="yesterday" aria-label="전날의 문구">
      <p class="yesterday-label">{previous_label} · {yesterday.isoformat()}</p>
      <p class="yesterday-quote" id="yesterday-quote">{escape(yesterday_quote['quote'])}</p>
      <p class="yesterday-author">— {escape(yesterday_quote['author'])}</p>
    </section>
    <footer>
      <p class="generated">마지막 생성 <time id="generated-at" datetime="{generated_kst.isoformat(timespec='seconds')}">{generated_kst.strftime('%Y.%m.%d %H:%M:%S')} KST</time></p>
      <details><summary>갱신 기록 보기</summary><p id="build-info">{provenance_text}</p></details>
      <p>하루 한 문장, 일상에 작은 깊이를 더하다.</p>
    </footer>
  </main>
</body>
</html>
'''


def atomic_write(output, content):
    """같은 폴더에 임시 파일을 완성한 뒤 교체하여 기존 HTML의 손상을 막습니다."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix=f".{output.name}.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="한국 날짜에 맞는 오늘의 한 문장을 생성합니다.")
    parser.add_argument("--date", type=parse_preview_date, help="날짜 미리보기: YYYY-MM-DD")
    parser.add_argument("--output", default="index.html", type=Path, help="출력 HTML 경로")
    args = parser.parse_args(argv)
    try:
        # 현재 시각은 한 번만 얻고, 날짜와 생성 시각 표시 모두에 사용합니다.
        generated_at = datetime.now(KST)
        target_date = choose_date(args.date, generated_at)
        quotes = load_quotes()
        html = generate_html(quotes, target_date, generated_at, is_preview=args.date is not None)
        atomic_write(args.output, html)
    except (OSError, ValueError) as error:
        print(f"생성 실패: {error}", file=sys.stderr)
        return 1
    print(f"문구 {len(quotes)}개 · 선택 날짜 {target_date} · {'날짜 미리보기' if args.date else '한국 날짜 기준'}")
    print(f"마지막 생성: {generated_at.strftime('%Y.%m.%d %H:%M:%S')} KST")
    print(f"HTML 생성 완료: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
