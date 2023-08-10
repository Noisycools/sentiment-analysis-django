from django.shortcuts import render, redirect
from bs4 import BeautifulSoup
from pytz import timezone
from string import punctuation
from heapq import nlargest
from deep_translator import GoogleTranslator
from rake_nltk import Rake
from json import dumps
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer

import gensim
import os
import json
import bs4
import datetime
import locale
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("window-size=1400,600")
from fake_useragent import UserAgent

ua = UserAgent()
user_agent = ua.random


def get_data(
    url,
    search_parameter,
    article_selector,
    title_selector,
    date_selector,
    content_selector,
):
    proxies = {
        "http": "http://190.61.88.147:8080",
        # "https": "https://190.61.88.147:8080",
    }

    html_text = requests.get(
        "{}{}".format(url, search_parameter.replace(" ", "+")),
        headers={"User-Agent": user_agent},
        proxies=proxies,
    ).text
    soup = BeautifulSoup(html_text, "lxml")

    locale.setlocale(locale.LC_TIME, "id_ID.UTF-8")
    "id_ID.UTF-8"
    local_tz = timezone("Asia/Jakarta")

    data = {}

    article_div = soup.select(article_selector)

    for article in article_div:
        if hasattr(article.find("a"), "attrs"):
            article_links = article.find("a").attrs["href"]
        html_content = requests.get(
            article_links,
            headers={"User-Agent": user_agent},
            proxies=proxies,
        ).text
        content_soup = BeautifulSoup(html_content, "lxml")

        if hasattr(content_soup.select_one(content_selector), "text"):
            content_div = content_soup.select_one(content_selector).text.replace(
                "\n", ""
            )
            if search_parameter.lower() in content_div.lower():
                article_dates = article.select_one(date_selector)
                date_text = []
                if article_dates is not None:
                    for x in article_dates:
                        if isinstance(x, bs4.element.NavigableString):
                            date_text.append(x.strip())

                output_date_text = " ".join(date_text).replace(" WIB", "")

                # datetime_object = datetime.datetime.strptime(
                #     output_date_text, "%A, %d %b %Y %H:%M"
                # )
                # output_dates = datetime_object.strftime("%Y-%m-%d %H:%M:%S")

                if hasattr(article.select_one(title_selector), "text"):
                    article_titles = article.select_one(title_selector).text

                # en_translator = GoogleTranslator(source="auto", target="en")
                # id_translator = GoogleTranslator(source="auto", target="id")

                # Define Indonesian stopwords
                stopwordsset = set(stopwords.words("indonesian"))

                # Tokenize the text into individual words
                tokens = word_tokenize(content_div)

                # Remove stopwords (common words that do not carry much meaning)
                tokens = [
                    token.lower()
                    for token in tokens
                    if token.lower() not in stopwordsset
                ]

                # Stem the words to their root form
                stemmer = PorterStemmer()
                tokens = [stemmer.stem(token) for token in tokens]

                # Join the tokens into a single string
                text_string = " ".join(tokens)

                module_dir = os.path.dirname(__file__)
                file_path = os.path.join(module_dir, "stopwords-id.txt")

                r = Rake(
                    language="indonesian",
                    include_repeated_phrases=False,
                    stopwords=open(file_path, "r"),
                )
                r.extract_keywords_from_text(text_string)

                data["topics"] = r.get_ranked_phrases()[0]

                positives = []
                negatives = []

                # if datetime_object.date() == datetime.datetime.now().date():
                data["judul-berita"] = {article_titles.strip()}
                data["tanggal-berita"] = {output_date_text.strip()}

                for rating, keyword in r.get_ranked_phrases_with_scores():
                    if rating > 5:
                        positives.append(keyword)
                    else:
                        negatives.append(keyword)

                data["positives"] = positives
                data["negatives"] = negatives

        return data


def convert_sets_to_lists(data):
    if isinstance(data, dict):
        return {key: convert_sets_to_lists(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_sets_to_lists(item) for item in data]
    elif isinstance(data, set):
        return list(data)
    else:
        return data


def index(request):
    query = request.GET.get("query", "")

    data = {
        "Detik": get_data(
            "https://www.detik.com/search/searchall?query=",
            query,
            "article",
            "h2.title",
            "span.date",
            "div.detail__body-text",
        ),
        "Viva": get_data(
            "https://www.viva.co.id/search?q=",
            query,
            "div.article-list-row",
            "h2",
            "div.article-list-date content_center",
            "div.main-content-detail",
        ),
        "Sindonews": get_data(
            "https://search.sindonews.com/go?q=",
            query,
            "div.news-content",
            "a",
            "div.news-date",
            "div#content",
        ),
        "Jawapos": get_data(
            "https://www.jawapos.com/search?q=",
            query,
            "div.latest__item",
            "a.latest__link",
            "date.latest__date",
            "article.read__content",
        ),
    }

    # Convert any sets to lists
    data = convert_sets_to_lists(data)

    data_not_null = {k: v for k, v in data.items() if v != {}}

    return render(
        request,
        "analytic/index.html",
        {
            "query": query.title(),
            "data": data_not_null,
            "data_dumps": dumps(data_not_null),
        },
    )
