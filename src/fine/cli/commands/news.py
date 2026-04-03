"""News command - 获取新闻数据"""

import os
import sys
import traceback
from pathlib import Path
from typing import List


def cmd_news(args) -> int:
    """获取新闻数据"""
    from fine.providers import MarketData
    from fine.providers.news_provider import _filter_news_by_keywords

    news_provider = args.provider or "akshare"
    start_date = args.start_time or ""
    end_date = args.end_time or ""
    result_dir = Path(os.path.expanduser(args.result)) if args.result else Path(".")
    keywords = args.keywords.split() if args.keywords else []

    try:
        market_data = MarketData(provider=news_provider)

        result_dir.mkdir(parents=True, exist_ok=True)

        def format_date_for_filename(dt_str: str) -> str:
            if not dt_str:
                return "all"
            return dt_str.replace(":", "").replace(" ", "").replace("-", "")

        def write_news_to_markdown(news_list: List, title: str) -> Path:
            start_fmt = format_date_for_filename(start_date)
            end_fmt = format_date_for_filename(end_date)

            filename = f"news-{news_provider}-{start_fmt}-{end_fmt}.md"
            result_file = result_dir / filename

            with open(result_file, "w", encoding="utf-8") as f:
                f.write(f"# {title} ({news_provider})\n\n")

                for news in news_list:
                    f.write(f"## {news.publish_date}\n\n")
                    f.write(f"- **标题**: {news.title}\n")
                    f.write(f"- **来源**: {news.source}\n")
                    if news.url:
                        f.write(f"- **链接**: {news.url}\n")
                    if news.content:
                        f.write(f"- **内容**: {news.content}\n")
                    f.write("\n---\n\n")

            return result_file

        # 获取新闻
        if news_provider == "akshare":
            news_list = market_data.get_news(news_type="efinance")
        elif news_provider == "xueqiu":
            news_list = market_data.get_news(news_type="stock")
        elif news_provider == "yicai":
            news_list = market_data.get_news(news_type="stock")
        elif news_provider == "sina":
            news_list = market_data.get_news(news_type="roll")
        elif news_provider == "wallstreetcn":
            news_list = market_data.get_news(news_type="global")
        elif news_provider == "cctv":
            news_list = market_data.get_news(news_type="cctv")
        elif news_provider == "economic":
            news_list = market_data.get_news(news_type="economic")
        else:
            print(f"Error: Unknown news provider: {news_provider}", file=sys.stderr)
            return 1

        # 关键词过滤
        if keywords:
            news_list = _filter_news_by_keywords(news_list, keywords)

        if news_list:
            title = "新闻"
            if news_provider == "cctv":
                title = "央视新闻"
            elif news_provider == "economic":
                title = "财经日历"
            result_file = write_news_to_markdown(news_list, title)
            print(str(result_file))
            return 0
        else:
            print("No news fetched", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1
