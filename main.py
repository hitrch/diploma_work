import pdfminer.high_level  # for reading pdf to string
import re  # for finding occurrences in string


def main():
    text = read_file()
    preprocessed_text = preprocess_text(text)
    places_to_analyze = find_places_to_analyze(text)


def read_file():
    file = open('test.pdf', 'rb')
    return pdfminer.high_level.extract_text(file)


def preprocess_text(text):
    text = remove_unnecessary_symbols(text, ["\n", "\r", "\t", "|"])
    text = remove_unnecessary_symbols_between_underscores(text)
    text = shrink_symbols(text, " ")
    text = shrink_symbols(text, "_")
    return text


def remove_unnecessary_symbols(text, symbols_to_remove):
    for symbol in symbols_to_remove:
        text = text.replace(symbol, '')
    return text


def shrink_symbols(text, symbol):
    shrink_index_list = [_.start() for _ in re.finditer(symbol, text)]

    for i in range(len(shrink_index_list) - 1):

        if shrink_index_list[i + 1] - shrink_index_list[i] == 1:
            # removing extra underscores
            text = text[0:shrink_index_list[i]] + text[shrink_index_list[i + 1]:len(text)]
            # reducing indexes of further underscores
            change_indexes_after_displacement(shrink_index_list, i, shrink_index_list[i + 1] - shrink_index_list[i])

    return text


def remove_unnecessary_symbols_between_underscores(text):
    array_with_unnecessary_symbols = [" "]

    underscores_index_list = [_.start() for _ in re.finditer('_', text)]
    for i in range(len(underscores_index_list) - 1):
        symbol = text[underscores_index_list[i] + 1]
        if any(item in symbol for item in array_with_unnecessary_symbols):
            text = text[0:underscores_index_list[i] + 1] + text[underscores_index_list[i] + 2:len(text)]
            change_indexes_after_displacement(underscores_index_list, i, 1)

    return text


def change_indexes_after_displacement(array, current_index, displacement):
    for i in range(len(array)):
        if i > current_index:
            array[i] = array[i] - displacement

def find_places_to_analyze(text):
    return []


if __name__ == "__main__":
    main()
