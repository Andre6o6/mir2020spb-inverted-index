# Индексатор и поисковик по коллекции текстов песен с Genius.com

## Задание 1. Булев поиск
### Сбор корпуса
В качестве корпуса использовался набор текстов песен, спарсеных с сайта Genius.com.
Для удовлетворения ограничений по объему он был дополнен [этим датасетом](https://www.kaggle.com/mousehead/songlyrics#songdata.csv).

[Ссылка на корпус](https://drive.google.com/file/d/1n3vnkxYtZKB1VSiLTPeXkh4KRs-LVjbi/view?usp=sharing).

### Токенизация и лексическая обработка текста
Текст разбит на токены по пробелам. В качестве стеммера используется `PorterStemmer` из `Gensim`.

### Построение индекса
Для построения индекся запустить скрипт `build_index_spimi.py`. Пример:
```
python build_index_spimi.py --memory 10
```
Для построения индекся используется алгоритм SPIMI. Для хранения индекса используется модуль `shelve`.

[Ссылка на индекс](https://drive.google.com/file/d/1DZyVhEZHbiUMX7n2u3wMAr80xm6wz8r1/view?usp=sharing)

### Поиск
Для поиска запустить скрипт `query.py`. Пример:
```
python query.py --q 'nothing AND else AND matters'
```
Булев поиск по индексу допускает оперции `AND`, `OR` и `NOT`, без скобок. Результаты поиска ранжируются по tf-idf.

Небольшой фронтенд: 
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1y357xySpDrLapK5orC9Xvkf7B9ZEtsbb)

## Задание 2. ML поиск
Данные:
* [Корпус](https://drive.google.com/file/d/1n3vnkxYtZKB1VSiLTPeXkh4KRs-LVjbi/view?usp=sharing)
* [Индекс](https://drive.google.com/file/d/1DZyVhEZHbiUMX7n2u3wMAr80xm6wz8r1/view?usp=sharing)
* [Предвычисленные эмбеддинги для всех текстов](https://drive.google.com/file/d/1XrA08ia3HNH8NCM7FHaHQf0RM-fWOLSt/view?usp=sharing)
* [Предвычесленный словарь дубликатов](https://drive.google.com/file/d/19pceTLC5gFSsZZ8WFNQ2zWLLZkh9as8B/view?usp=sharing)

### ML поиск
Для поиска запустить скрипт `query_ml.py`. Пример:
```
python query_ml.py --q 'nothing else matters'
```
Сначала проводится широкий булев поиск, потом top-N кандидатов переранжируюся 
по косинусову расстоянию их DistilBERT эмбеддингов и эмбеддинга запроса.

Синтаксис запроса:
```
'word1 word2 word3'
'word1 word2 NOT word3'
'word1 word2 NOT(word3 word4)'
```
что в булевом поиске бы соответствовало:
```
word1 OR word2 OR word3
(word1 OR word2) AND NOT word3
(word1 OR word2) AND NOT(word3 OR word4)
```
### Поиск дубликатов
Для поиска дубликатов запустить скрипт `duplicates.py`. Пример:
```
python duplicates.py
```
Поиск дупликатов проводится с помощью kNN по эмбеддингам всех текстов. 
Используется имплементация kNN из библиотеки [faiss](https://github.com/facebookresearch/faiss).

Опции:
* `python duplicates.py` вычислит словарь дубликатов если он еще не вычислен и сохранит его в формате `.pkl`.
* `python duplicates.py --save` выведет названия дубликатов для **всех** песен в текстовый файл.
* `python duplicates.py --band BAND_NAME` выведет названия дубликатов песен группы BAND_NAME.
* `python duplicates.py --find FIND_FILE` выведет названия дубликатов песни из файла FIND_FILE (если он явсяется частью корпуса).
