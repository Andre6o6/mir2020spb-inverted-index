# Индексатор и поисковик по коллекции текстов песен с Genius.com

## Сбор корпуса
В качестве корпуса использовался набор текстов песен, спарсеных с сайта Genius.com.
Для удовлетворения ограничений по объему он был дополнен [этим датасетом](https://www.kaggle.com/mousehead/songlyrics#songdata.csv).

[Ссылка на корпус](https://drive.google.com/file/d/1wwgx6kUfZfw1xDtUqTWNE2GxPbIE3RHT/view?usp=sharing).

## Токенизация и лексическая обработка текста
Текст разбит на токены по пробелам. В качестве стеммера используется `PorterStemmer` из `Gensim`.

## Построение индекса
Для построения индекся используется алгоритм SPIMI. Для хранения индекса используется модуль `shelve`.

[Ссылка на индекс](https://drive.google.com/file/d/1g0oNegKraNhnGN_uvp-XkMVEVSghjYnt/view?usp=sharing)

## Поиск
Булев поиск по индексу допускает оперции `AND`, `OR` и `NOT`, без скобок. Результаты поиска ранжируются по tf-idf.

Небольшой фронтенд: 
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1y357xySpDrLapK5orC9Xvkf7B9ZEtsbb)
