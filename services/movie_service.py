from typing import List, Dict, Any

import requests

from config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
HEADERS = {
    "Authorization": f"Bearer {TMDB_API_KEY}",
    "accept": "application/json"
}


def get_trending_movies(time_window: str = "day") -> List[Dict[str, Any]]:
    """
    Get trending movies for the day or week.

    :param time_window: 'day' or 'week'
    :return: List of trending movies
    """
    url = f"{BASE_URL}/trending/movie/{time_window}"
    params = {"language": "zh-CN"}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("results", [])


def search_movies(query: str) -> List[Dict[str, Any]]:
    """
    Search for movies based on a query string.

    :param query: Search query
    :return: List of movie search results
    """
    url = f"{BASE_URL}/search/movie"
    params = {"query": query, "language": "zh-CN", "page": 1}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    for movie in results:
        if movie['poster_path']:
            movie['poster_url'] = f"{IMAGE_BASE_URL}{movie['poster_path']}"
        else:
            movie['poster_url'] = None
    return results


def get_movie_details(movie_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific movie.

    :param movie_id: TMDB movie ID
    :return: Dictionary containing movie details
    """
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {"language": "zh-CN", "append_to_response": "credits,reviews"}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    movie = response.json()
    if movie['poster_path']:
        movie['poster_url'] = f"{IMAGE_BASE_URL}{movie['poster_path']}"
    else:
        movie['poster_url'] = None
    return movie


def get_trending_tv_shows(time_window: str = "day") -> List[Dict[str, Any]]:
    """
    Get trending TV shows for the day or week.

    :param time_window: 'day' or 'week'
    :return: List of trending TV shows
    """
    url = f"{BASE_URL}/trending/tv/{time_window}"
    params = {"language": "zh-CN"}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("results", [])


def search_tv_shows(query: str) -> List[Dict[str, Any]]:
    """
    Search for TV shows based on a query string.

    :param query: Search query
    :return: List of TV show search results
    """
    url = f"{BASE_URL}/search/tv"
    params = {"query": query, "language": "zh-CN", "page": 1}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    for movie in results:
        if movie['poster_path']:
            movie['poster_url'] = f"{IMAGE_BASE_URL}{movie['poster_path']}"
        else:
            movie['poster_url'] = None
    return data.get("results", [])


def get_tv_show_details(tv_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific TV show.

    :param tv_id: TMDB TV show ID
    :return: Dictionary containing TV show details
    """
    url = f"{BASE_URL}/tv/{tv_id}"
    params = {"language": "zh-CN"}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    movie = response.json()
    if movie['poster_path']:
        movie['poster_url'] = f"{IMAGE_BASE_URL}{movie['poster_path']}"
    else:
        movie['poster_url'] = None
    return movie


def get_trending_items(time_window: str = "day") -> List[Dict[str, Any]]:
    """
    Get trending movies and TV shows for the day or week.

    :param time_window: 'day' or 'week'
    :return: List of trending movies and TV shows
    """
    movies = get_trending_movies(time_window)
    tv_shows = get_trending_tv_shows(time_window)

    # 组合 movies 和 tv_shows
    trending_items = movies + tv_shows

    # 添加 item_type 字段以便区分是电影还是电视剧
    for item in trending_items:
        if 'title' in item:
            item['item_type'] = 'movie'
        elif 'name' in item:
            item['item_type'] = 'tv'

    return trending_items