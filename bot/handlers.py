import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from data.database import add_to_watchlist, get_watchlist, remove_from_watchlist, is_in_watchlist
from services.movie_service import search_movies, search_tv_shows, get_movie_details, get_tv_show_details, \
    get_trending_items


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"你好 {user.mention_html()}！我是你的电影和电视剧机器人。使用 /help 查看我能做什么。"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = """
    以下是你可以使用的命令：
    /search <标题> - 搜索电影或电视剧
    /add <类型> <ID> - 将电影或电视剧添加到你的观看列表
    /watchlist - 查看你的观看列表
    /remove <ID> - 从你的观看列表中删除一个项目
    """
    await update.message.reply_text(help_text)


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for movies and TV shows and display results with inline keyboard."""
    if update.message:
        query = ' '.join(context.args)
        if not query:
            await update.message.reply_text("请在 /search 后提供搜索词")
            return
    else:  # 处理回调查询的情况
        query = context.user_data.get('last_search_query', '')
        if not query:
            await update.callback_query.message.reply_text("无法找到上一次的搜索查询。请尝试新的搜索。")
            return

    # 保存搜索查询以便后续使用
    context.user_data['last_search_query'] = query

    movies = search_movies(query)
    tv_shows = search_tv_shows(query)

    if not movies and not tv_shows:
        message = "没有找到相关结果。"
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)
        return

    # 分别对电影和电视剧进行排序
    movies = sorted(movies, key=lambda x: x.get('popularity', 0), reverse=True)
    tv_shows = sorted(tv_shows, key=lambda x: x.get('popularity', 0), reverse=True)

    keyboard = []
    # 添加电影结果
    if movies:
        keyboard.append([InlineKeyboardButton("电影", callback_data="header_movie")])
        for item in movies[:5]:  # 限制为前5个电影结果
            title = item['title']
            year = item['release_date'][:4]
            rating = f"⭐ {item['vote_average']:.1f}" if item.get('vote_average') else "暂无评分"
            button_text = f"🎬 {title} ({year}) - {rating}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"movie_{item['id']}")])

    # 添加电视剧结果
    if tv_shows:
        keyboard.append([InlineKeyboardButton("电视剧", callback_data="header_tv")])
        for item in tv_shows[:5]:  # 限制为前5个电视剧结果
            title = item['name']
            year = item['first_air_date'][:4]
            rating = f"⭐ {item['vote_average']:.1f}" if item.get('vote_average') else "暂无评分"
            button_text = f"📺 {title} ({year}) - {rating}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"tv_{item['id']}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = f"搜索结果 - \"{query}\":"

    if update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    else:
        try:
            # 尝试编辑现有消息
            await update.callback_query.message.edit_text(message_text, reply_markup=reply_markup)
        except telegram.error.BadRequest as e:
            if str(e) == "Message is not modified":
                # 如果消息没有改变，我们可以忽略这个错误
                pass
            elif "There is no text in the message to edit" in str(e):
                # 如果原消息没有文本，发送新消息
                await update.callback_query.message.reply_text(message_text, reply_markup=reply_markup)
            else:
                # 对于其他错误，重新引发异常
                raise


async def item_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display details for a movie or TV show."""
    query = update.callback_query
    await query.answer()
    item_type, item_id = query.data.split('_')
    item_id = int(item_id)
    user_id = update.effective_user.id

    if item_type == 'movie':
        details = get_movie_details(item_id)
        title = details['title']
        release_date = details['release_date']
        overview = details['overview']
        poster_url = details.get('poster_url')
    else:  # TV show
        details = get_tv_show_details(item_id)
        title = details['name']
        release_date = details['first_air_date']
        overview = details['overview']
        poster_url = details.get('poster_url')

    details_text = (f"{'电影' if item_type == 'movie' else '电视剧'}: {title}\n"
                    f"发布日期: {release_date}\n"
                    f"评分: {details['vote_average']}/10\n\n"
                    f"概述: {overview[:200]}...")

    # 检查项目是否已经在观看列表中
    in_watchlist = is_in_watchlist(user_id, item_id, item_type)

    keyboard = [
        [
            InlineKeyboardButton("返回搜索结果", callback_data=f"back_to_search"),
        ]
    ]

    # 根据是否在观看列表中来决定显示哪个按钮
    if in_watchlist:
        keyboard[0].append(InlineKeyboardButton("已添加到观看列表", callback_data="dummy_action"))
    else:
        keyboard[0].append(InlineKeyboardButton("添加到观看列表", callback_data=f"add_{item_type}_{item_id}"))

    reply_markup = InlineKeyboardMarkup(keyboard)

    if poster_url:
        await query.message.reply_photo(photo=poster_url, caption=details_text, reply_markup=reply_markup)
        await query.message.delete()
    else:
        await query.edit_message_text(text=details_text, reply_markup=reply_markup)

async def view_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View the user's watchlist."""
    user_id = update.effective_user.id
    watchlist = get_watchlist(user_id)

    if not watchlist:
        await update.message.reply_text("你的观看列表是空的。")
        return

    response = "你的观看列表：\n\n"
    for item in watchlist:
        item_type = "电影" if item.item_type == "movie" else "电视剧"
        response += f"- {item.title} ({item_type}) - ID: {item.item_id}\n"

    response += "\n要删除一个项目，请使用 /remove <ID>"
    await update.message.reply_text(response)

async def remove_from_watchlist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a movie or TV show from the watchlist."""
    if not context.args:
        await update.message.reply_text("请提供要删除的项目的ID。")
        return

    user_id = update.effective_user.id
    item_id = int(context.args[0])

    if remove_from_watchlist(user_id, item_id):
        await update.message.reply_text("项目已从你的观看列表中删除。")
    else:
        await update.message.reply_text("在你的观看列表中未找到该项目。")

async def movie_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display movie details and option to add to watchlist."""
    query = update.callback_query
    await query.answer()

    movie_id = int(query.data.split('_')[1])
    movie = get_movie_details(movie_id)

    details = f"标题: {movie['title']}\n"
    details += f"上映日期: {movie['release_date']}\n"
    details += f"评分: {movie['vote_average']}/10\n"
    details += f"概述: {movie['overview'][:200]}...\n"

    keyboard = [
        [InlineKeyboardButton("添加到观看列表", callback_data=f"add_{movie_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if movie['poster_url']:
        await query.message.reply_photo(movie['poster_url'], caption=details, reply_markup=reply_markup)
    else:
        await query.message.reply_text(details, reply_markup=reply_markup)


async def add_to_watchlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a movie or TV show to the watchlist."""
    query = update.callback_query
    await query.answer()

    item_type, item_id = query.data.split('_')[1:]
    item_id = int(item_id)
    user_id = update.effective_user.id

    if item_type == 'movie':
        details = get_movie_details(item_id)
        title = details['title']
    else:  # TV show
        details = get_tv_show_details(item_id)
        title = details['name']

    # 假设你有一个 add_to_watchlist 函数在 database 模块中
    add_to_watchlist(user_id, item_id, item_type,title)
    await query.message.reply_text(f"已将 {title} 添加到你的观看列表！")

    # 更新按钮状态
    keyboard = [
        [
            InlineKeyboardButton("返回搜索结果", callback_data=f"back_to_search"),
            InlineKeyboardButton("已添加到观看列表", callback_data="dummy_action")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith(("movie_", "tv_")):
        await item_details(update, context)
    elif query.data == "back_to_search":
        await back_to_search(update, context)
    elif query.data.startswith("add_"):
        # 处理添加到观看列表的逻辑
        await add_to_watchlist_callback(update, context)


async def back_to_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    last_search_query = context.user_data.get('last_search_query')
    if last_search_query:
        # 重新执行搜索
        await search(update, context)
    else:
        await query.message.reply_text("无法返回上一次搜索结果。请尝试新的搜索。")

async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /trending command."""
    time_window = context.args[0] if context.args and context.args[0] in ['day', 'week'] else 'day'
    trending_items = get_trending_items(time_window)

    # 分别获取电影和电视剧
    movies = [item for item in trending_items if item['item_type'] == 'movie'][:5]
    tv_shows = [item for item in trending_items if item['item_type'] == 'tv'][:5]

    # 创建消息
    message = "🎬 *Trending Movies:*\n"
    for idx, movie in enumerate(movies, start=1):
        message += f"{idx}. *{movie['title']}* ({movie['release_date']})\n"

    message += "\n📺 *Trending TV Shows:*\n"
    for idx, tv_show in enumerate(tv_shows, start=1):
        message += f"{idx}. *{tv_show['name']}* ({tv_show['first_air_date']})\n"

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)



