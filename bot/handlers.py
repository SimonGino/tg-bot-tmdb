from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from data.database import add_to_watchlist, get_watchlist, remove_from_watchlist
from services.movie_service import search_movies, search_tv_shows, get_movie_details, get_tv_show_details


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
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("请在 /search 后提供搜索词")
        return

    movies = search_movies(query)
    tv_shows = search_tv_shows(query)

    if not movies and not tv_shows:
        await update.message.reply_text("没有找到相关结果。")
        return

    keyboard = []
    for movie in movies[:5]:  # Limit to top 5 movie results
        keywords = ', '.join(movie.get('keywords', [])[:3])  # Get up to 3 keywords
        button_text = f"🎬 {movie['title']} ({movie['release_date'][:4]}) - {keywords}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"movie_{movie['id']}")])

    for show in tv_shows[:5]:  # Limit to top 5 TV show results
        keywords = ', '.join(show.get('keywords', [])[:3])  # Get up to 3 keywords
        button_text = f"📺 {show['name']} ({show['first_air_date'][:4]}) - {keywords}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"tv_{show['id']}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("搜索结果：", reply_markup=reply_markup)

async def item_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display details for a movie or TV show."""
    query = update.callback_query
    await query.answer()
    item_type, item_id = query.data.split('_')
    item_id = int(item_id)

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

    keyboard = [[InlineKeyboardButton("添加到观看列表", callback_data=f"add_{item_type}_{item_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if poster_url:
        await query.message.reply_photo(photo=poster_url, caption=details_text, reply_markup=reply_markup)
        await query.message.delete()
    else:
        await query.edit_message_text(text=details_text, reply_markup=reply_markup)

async def add_to_watchlist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a movie or TV show to the watchlist."""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("请使用以下格式：/add <类型> <ID>\n例如：/add movie 550")
        return

    item_type = args[0].lower()
    item_id = int(args[1])
    user_id = update.effective_user.id

    if item_type == "movie":
        details = get_movie_details(item_id)
        title = details['title']
    elif item_type == "tv":
        details = get_tv_show_details(item_id)
        title = details['name']
    else:
        await update.message.reply_text("无效的类型。请使用 'movie' 或 'tv'。")
        return

    add_to_watchlist(user_id, item_id, item_type, title)
    await update.message.reply_text(f"已将 {title} 添加到你的观看列表！")

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