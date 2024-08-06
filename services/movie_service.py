from typing import List, Dict, Any
from functools import lru_cache
import requests

from config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
HEADERS = {
    "Authorization": f"Bearer {TMDB_API_KEY}",
    "accept": "application/json"
}

def add_poster_url(item: Dict[str, Any]) -> None:
    """为项目添加海报URL"""
    if item['poster_path']:
        item['poster_url'] = f"{IMAGE_BASE_URL}{item['poster_path']}"
    else:
        item['poster_url'] = None

def make_api_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """发送API请求并返回JSON数据"""
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

@lru_cache(maxsize=32)
def get_trending_movies(time_window: str = "day") -> List[Dict[str, Any]]:
    """获取热门电影"""
    url = f"{BASE_URL}/trending/movie/{time_window}"
    params = {"language": "zh-CN"}
    data = make_api_request(url, params)
    results = data.get("results", [])
    for movie in results:
        add_poster_url(movie)
    return results

@lru_cache(maxsize=32)
def search_movies(query: str) -> List[Dict[str, Any]]:
    """搜索电影"""
    url = f"{BASE_URL}/search/movie"
    params = {"query": query, "language": "zh-CN", "page": 1}
    data = make_api_request(url, params)
    results = data.get("results", [])
    for movie in results:
        add_poster_url(movie)
    return results

@lru_cache(maxsize=128)
def get_movie_details(movie_id: int) -> Dict[str, Any]:
    """获取电影详情"""
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {"language": "zh-CN", "append_to_response": "credits,reviews"}
    movie = make_api_request(url, params)
    add_poster_url(movie)
    return movie

@lru_cache(maxsize=32)
def get_trending_tv_shows(time_window: str = "day") -> List[Dict[str, Any]]:
    """获取热门电视节目"""
    url = f"{BASE_URL}/trending/tv/{time_window}"
    params = {"language": "zh-CN"}
    data = make_api_request(url, params)
    results = data.get("results", [])
    for show in results:
        add_poster_url(show)
    return results

@lru_cache(maxsize=32)
def search_tv_shows(query: str) -> List[Dict[str, Any]]:
    """搜索电视节目"""
    url = f"{BASE_URL}/search/tv"
    params = {"query": query, "language": "zh-CN", "page": 1}
    data = make_api_request(url, params)
    results = data.get("results", [])
    for show in results:
        add_poster_url(show)
    return results

@lru_cache(maxsize=128)
def get_tv_show_details(tv_id: int) -> Dict[str, Any]:
    """获取电视节目详情"""
    url = f"{BASE_URL}/tv/{tv_id}"
    params = {"language": "zh-CN"}
    show = make_api_request(url, params)
    add_poster_url(show)
    return show

def get_trending_items(time_window: str = "day") -> List[Dict[str, Any]]:
    """获取热门电影和电视节目"""
    movies = get_trending_movies(time_window)
    tv_shows = get_trending_tv_shows(time_window)

    trending_items = movies + tv_shows

    for item in trending_items:
        item['item_type'] = 'movie' if 'title' in item else 'tv'

    return trending_items