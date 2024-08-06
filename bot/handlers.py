from datetime import datetime
from typing import List, Dict, Any

import telegram
from sqlalchemy.orm import joinedload
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from data.database import Session, WatchlistItem
from data.database import add_to_watchlist, remove_from_watchlist, is_in_watchlist, get_all_subscribers, \
    add_subscriber
from services.movie_service import search_movies, search_tv_shows, get_movie_details, get_tv_show_details, \
    get_trending_items


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"你好 {user.mention_html()}！我是你的电影和电视剧机器人。使用 /help 查看我能做什么。"
    )
    add_subscriber(user.id)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
    以下是你可以使用的命令：
    /search <标题> - 搜索电影或电视剧
    /add <类型> <ID> - 将电影或电视剧添加到你的观看列表
    /watchlist - 查看你的观看列表
    /remove <ID> - 从你的观看列表中删除一个项目
    /trending - 查看热门电影和电视剧
    """
    await update.message.reply_text(help_text)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = ' '.join(context.args) if update.message else context.user_data.get('last_search_query', '')
    if not query:
        await (update.message or update.callback_query.message).reply_text("请提供搜索词")
        return

    context.user_data['last_search_query'] = query
    movies = search_movies(query)
    tv_shows = search_tv_shows(query)

    if not movies and not tv_shows:
        await (update.message or update.callback_query.message).reply_text("没有找到相关结果。")
        return

    keyboard = create_search_keyboard(movies, tv_shows)
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = f"搜索结果 - \"{query}\":"

    if update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    else:
        try:
            await update.callback_query.message.edit_text(message_text, reply_markup=reply_markup)
        except telegram.error.BadRequest as e:
            if "Message is not modified" not in str(e):
                await update.callback_query.message.reply_text(message_text, reply_markup=reply_markup)

def create_search_keyboard(movies: List[Dict[str, Any]], tv_shows: List[Dict[str, Any]]) -> List[List[InlineKeyboardButton]]:
    keyboard = []
    for media_type, items in [("电影", movies), ("电视剧", tv_shows)]:
        if items:
            keyboard.append([InlineKeyboardButton(media_type, callback_data=f"header_{media_type}")])
            for item in sorted(items, key=lambda x: x.get('popularity', 0), reverse=True)[:5]:
                title = item['title'] if media_type == "电影" else item['name']
                year = item['release_date'][:4] if media_type == "电影" else item['first_air_date'][:4]
                rating = f"⭐ {item['vote_average']:.1f}" if item.get('vote_average') else "暂无评分"
                button_text = f"{'🎬' if media_type == '电影' else '📺'} {title} ({year}) - {rating}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"{'movie' if media_type == '电影' else 'tv'}_{item['id']}")])
    return keyboard

async def item_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    item_type, item_id = query.data.split('_')
    item_id = int(item_id)
    user_id = update.effective_user.id

    details = get_movie_details(item_id) if item_type == 'movie' else get_tv_show_details(item_id)
    title = details['title'] if item_type == 'movie' else details['name']
    release_date = details['release_date'] if item_type == 'movie' else details['first_air_date']
    
    details_text = (f"{'电影' if item_type == 'movie' else '电视剧'}: {title}\n"
                    f"发布日期: {release_date}\n"
                    f"评分: {details['vote_average']}/10\n\n"
                    f"概述: {details['overview'][:200]}...")

    in_watchlist = is_in_watchlist(user_id, item_id, item_type)
    keyboard = [
        [
            InlineKeyboardButton("返回搜索结果", callback_data="back_to_search"),
            InlineKeyboardButton("已添加到观看列表" if in_watchlist else "添加到观看列表", 
                                 callback_data="dummy_action" if in_watchlist else f"add_{item_type}_{item_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if details.get('poster_url'):
        await query.message.reply_photo(photo=details['poster_url'], caption=details_text, reply_markup=reply_markup)
        await query.message.delete()
    else:
        await query.edit_message_text(text=details_text, reply_markup=reply_markup)

async def view_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    with Session() as session:
        # 使用 joinedload 预加载所需的关系
        watchlist = session.query(WatchlistItem).filter_by(user_id=user_id).options(joinedload('*')).all()

        if not watchlist:
            await update.message.reply_text("你的观看列表是空的。")
            return

        response = "你的观看列表：\n\n" + "\n".join(
            f"- {item.title} ({'电影' if item.item_type == 'movie' else '电视剧'}) - ID: {item.item_id}"
            for item in watchlist
        ) + "\n\n要删除一个项目，请使用 /remove <ID>"
    
    await update.message.reply_text(response)

async def remove_from_watchlist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("请提供要删除的项目的ID。")
        return

    user_id = update.effective_user.id
    item_id = int(context.args[0])

    message = "项目已从你的观看列表中删除。" if remove_from_watchlist(user_id, item_id) else "在你的观看列表中未找到该项目。"
    await update.message.reply_text(message)

async def add_to_watchlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    item_type, item_id = query.data.split('_')[1:]
    item_id = int(item_id)
    user_id = update.effective_user.id

    details = get_movie_details(item_id) if item_type == 'movie' else get_tv_show_details(item_id)
    title = details['title'] if item_type == 'movie' else details['name']

    if is_in_watchlist(user_id, item_id, item_type):
        await query.message.reply_text(f"{title} 已经在你的观看列表中！")
    else:
        add_to_watchlist(user_id, item_id, item_type, title)
        await query.message.reply_text(f"已将 {title} 添加到你的观看列表！")

    keyboard = [
        [
            InlineKeyboardButton("返回搜索结果", callback_data="back_to_search"),
            InlineKeyboardButton("已添加到观看列表", callback_data="dummy_action")
        ]
    ]
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data.startswith(("movie_", "tv_")):
        await item_details(update, context)
    elif query.data == "back_to_search":
        await back_to_search(update, context)
    elif query.data.startswith("add_"):
        await add_to_watchlist_callback(update, context)

async def back_to_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    last_search_query = context.user_data.get('last_search_query')
    if last_search_query:
        await search(update, context)
    else:
        await query.message.reply_text("无法返回上一次搜索结果。请尝试新的搜索。")

async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    time_window = context.args[0] if context.args and context.args[0] in ['day', 'week'] else 'week'
    trending_items = get_trending_items(time_window)

    movies = [item for item in trending_items if item['item_type'] == 'movie'][:5]
    tv_shows = [item for item in trending_items if item['item_type'] == 'tv'][:5]

    top_movie = movies[0]
    top_movie_poster_url = top_movie['poster_url']

    current_date = datetime.now().strftime("%Y-%m-%d")

    message = f"📅 *Date:* {current_date}\n"
    message += f"📊 *Trending:* {time_window.capitalize()}\n"
    message += "🔗 *GitHub:* [SimonGino/tg-bot-tmdb](https://github.com/SimonGino/tg-bot-tmdb)\n\n"

    message += "🎬 *Trending Movies:*\n" + "\n".join(
        f"{idx}. [{movie['title']}] 评分: {movie['vote_average']}"
        for idx, movie in enumerate(movies, start=1)
    )

    message += "\n\n📺 *Trending TV Shows:*\n" + "\n".join(
        f"{idx}. [{tv_show['name']}] 评分: {tv_show['vote_average']}"
        for idx, tv_show in enumerate(tv_shows, start=1)
    )

    if top_movie_poster_url:
        await update.message.reply_photo(photo=top_movie_poster_url, caption=message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def send_weekly_trending(context: ContextTypes.DEFAULT_TYPE) -> None:
    time_window = 'week'
    trending_items = get_trending_items(time_window)

    movies = [item for item in trending_items if item['item_type'] == 'movie'][:5]
    tv_shows = [item for item in trending_items if item['item_type'] == 'tv'][:5]

    top_movie = movies[0]
    top_movie_poster_url = top_movie['poster_url']

    current_date = datetime.now().strftime("%Y-%m-%d")

    message = f"📅 *Date:* {current_date}\n"
    message += f"📊 *Trending:* {time_window.capitalize()}\n"
    message += "🔗 *GitHub:* [SimonGino/tg-bot-tmdb](https://github.com/SimonGino/tg-bot-tmdb)\n\n"

    message += "🎬 *Trending Movies:*\n" + "\n".join(
        f"{idx}. [{movie['title']}] 评分: {movie['vote_average']}"
        for idx, movie in enumerate(movies, start=1)
    )

    message += "\n\n📺 *Trending TV Shows:*\n" + "\n".join(
        f"{idx}. [{tv_show['name']}] 评分: {tv_show['vote_average']}"
        for idx, tv_show in enumerate(tv_shows, start=1)
    )

    user_chat_ids = get_all_subscribers()

    for chat_id in user_chat_ids:
        if top_movie_poster_url:
            await context.bot.send_photo(chat_id=chat_id, photo=top_movie_poster_url, caption=message,
                                         parse_mode=ParseMode.MARKDOWN)
        else:
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN)