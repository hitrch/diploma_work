import json
from io import BytesIO

import pdfminer.high_level  # for reading pdf to string
import re  # for finding occurrences in string

from flask import Flask, make_response, request
from flask_restful import Api, Resource, reqparse

app = Flask(__name__)
api = Api()


class Main(Resource):
    def post(self):
        pdf_file = request.files['file']
        data = main(pdf_file)
        resp = make_response(json.dumps(data))
        resp.headers['Access-Control-Allow-Origin'] = 'http://localhost:4200'
        resp.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PATCH, PUT, DELETE, OPTIONS'
        return resp

    def options(self):
        return {'Allow': '*'}, 200, \
               {'Access-Control-Allow-Origin': '*',
                "Access-Control-Allow-Headers": "*",
                'Access-Control-Allow-Methods': '*'}


api.add_resource(Main, "/analyze")
api.init_app(app)


class Data:
    def __init__(self, data_array, corresponding_line):
        self.data_array = data_array
        self.corresponding_line = corresponding_line


def main(file):
    if file:
        text = pdfminer.high_level.extract_text(BytesIO(file.read()))
    else:
        text = read_file()

    text = preprocess_text(text)
    prepared_data_for_classification = corresponding_text_finding_algorithm(text)
    properties_in_document = find_properties_of_main_person_dictionary(prepared_data_for_classification)
    return [properties_in_document, text]
    # for item in properties_in_document:
    #     print(item)


def read_file():
    file = open("test-file.pdf", 'rb')
    return pdfminer.high_level.extract_text(file)


def corresponding_text_finding_algorithm(text):
    return analyze_text(text)


def preprocess_text(text):
    text = remove_unnecessary_symbols(text, ["\r", "\t", "|"])
    text = remove_unnecessary_symbols_between_underscores(text)
    text = shrink_symbols(text, " ")
    text = shrink_symbols(text, "_")
    text = remove_spaces_in_first_place_of_row(text)
    text = remove_newline_if_empty_line(text)
    text = transform_string_to_array_based_on_newlines(text)
    text = shrink_lines_specified_for_same_data(text)
    return text


def remove_unnecessary_symbols(text, symbols_to_remove):
    for symbol in symbols_to_remove:
        text = text.replace(symbol, ' ')
    return text


def shrink_lines_specified_for_same_data(text):
    for i in range(len(text)):
        text[i] = text[i].strip()

    underscore_indexes = find_indexes(text, "_")
    index_array_to_delete = []

    for index in range(len(underscore_indexes)):
        if underscore_indexes[index] + 1 < len(text) - 1 and text[underscore_indexes[index] + 1] == '_':
            opening_bracket_indexes = find_indexes(text[underscore_indexes[index] + 2], "(")
            if not opening_bracket_indexes or not opening_bracket_indexes[0] <= 2 or text[
                underscore_indexes[index]] == '_':
                index_array_to_delete.append(underscore_indexes[index] + 1)

    index_array_to_delete.reverse()

    for index in range(len(index_array_to_delete)):
        text.pop(index_array_to_delete[index])

    return text


def shrink_symbols(text, symbol):
    shrink_index_list = [_.start() for _ in re.finditer(symbol, text)]

    for i in range(len(shrink_index_list) - 1):
        if shrink_index_list[i + 1] - shrink_index_list[i] == 1:
            # removing extra symbols
            text = text[0:shrink_index_list[i]] + text[shrink_index_list[i + 1]:len(text)]
            # reducing indexes of further symbols
            change_indexes_after_displacement(shrink_index_list, i, shrink_index_list[i + 1] - shrink_index_list[i])

    return text


def remove_spaces_in_first_place_of_row(text):
    newline_index_list = [_.start() for _ in re.finditer('\n', text)]

    for i in range(len(newline_index_list)):
        if newline_index_list[i] + 1 < len(text) and text[newline_index_list[i] + 1] == ' ':
            text = text[0:newline_index_list[i] + 1] + text[newline_index_list[i] + 2:len(text)]
            change_indexes_after_displacement(newline_index_list, i, 1)

    return text


def remove_newline_if_empty_line(text):
    newline_index_list = [_.start() for _ in re.finditer('\n', text)]

    for i in range(len(newline_index_list)):
        if newline_index_list[i] + 1 <= len(text) and text[newline_index_list[i] + 1] == '\n':
            text = text[0:newline_index_list[i]] + text[newline_index_list[i] + 1:len(text)]
            change_indexes_after_displacement(newline_index_list, i, 1)

    return text


def transform_string_to_array_based_on_newlines(text):
    text_array = []
    newline_index_list = [_.start() for _ in re.finditer('\n', text)]

    for i in range(len(newline_index_list)):
        if i == 0:
            text_array.append(text[0:newline_index_list[i]])
        else:
            text_array.append(text[newline_index_list[i - 1] + 1:newline_index_list[i]])

    return text_array


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


def analyze_text(text_array):
    data = []
    should_skip_next_counter = 0
    index_array = find_indexes(text_array, '_')
    for index in range(len(index_array)):
        if should_skip_next_counter == 0:
            step_data = find_text_corresponding_to_underscores(text_array, index_array, index)
            should_skip_next_counter = step_data[0]
            # print(step_data[1], index_array[index])
            data.append(Data(step_data[1], index_array[index] + 1))
        else:
            should_skip_next_counter -= 1
    return data


def find_indexes(data, symbol):
    index_array = []
    if isinstance(data, str):
        if symbol == "(":
            return [_.start() for _ in re.finditer("\(", data)]
        elif symbol == ")":
            return [_.start() for _ in re.finditer("\)", data)]

        return [_.start() for _ in re.finditer(symbol, data)]
    else:
        for i in range(len(data)):
            if symbol in data[i]:
                index_array.append(i)

    return index_array


def find_text_corresponding_to_underscores(text_array, index_array, index):
    corresponding_texts_array = []
    should_skip_next_lines_counter = 0
    underscore_in_line_index_array = find_indexes(text_array[index_array[index]], '_')

    if len(underscore_in_line_index_array) == 1:
        down_data = search_down(text_array, index_array, index)
        should_skip_next_lines_counter += down_data[0]

        if len(down_data[1]) > 0:
            corresponding_texts_array = down_data[1]
            return [should_skip_next_lines_counter, [corresponding_texts_array]]

    up_option = search_current_line_and_above(text_array, index_array, index, underscore_in_line_index_array)

    if up_option:
        if type(up_option) == list:
            corresponding_texts_array.extend(up_option)
        else:
            corresponding_texts_array.append(up_option)

    return [should_skip_next_lines_counter, corresponding_texts_array]


def search_down(text_array, index_array, index):
    should_skip_next_lines_counter = 0
    corresponding_text = ''

    if index < len(text_array):
        # in case corresponding text takes multiple rows we should consider it as one piece
        opening_bracket_indexes = find_indexes(text_array[index_array[index] + 1], "(")
        opening_brackets_count = len(opening_bracket_indexes)

        # checking if there is at least one opening bracket near the start of the line
        if opening_brackets_count and opening_bracket_indexes[0] <= 2:
            closing_brackets_count = len(find_indexes(text_array[index_array[index] + 1], ")"))

            if opening_brackets_count != closing_brackets_count:
                processed_data = process_lines_with_multiline_corresponding_text(
                    text_array, index_array, index, opening_brackets_count, closing_brackets_count
                )
                should_skip_next_lines_counter = processed_data[0]
                corresponding_text = processed_data[1]
            else:
                corresponding_text = text_array[index_array[index] + 1]
                corresponding_text = corresponding_text[1:len(corresponding_text) - 1]

    return [should_skip_next_lines_counter, corresponding_text]


def process_lines_with_multiline_corresponding_text(
        text_array,
        index_array,
        index,
        opening_brackets_count,
        closing_brackets_count
):
    should_skip_next_lines_counter = 0
    current_index = index_array[index] + 1
    corresponding_text = text_array[current_index]

    while opening_brackets_count != closing_brackets_count:
        opening_brackets_count += len(find_indexes(text_array[current_index + 1], "("))
        closing_brackets_count += len(find_indexes(text_array[current_index + 1], ")"))
        corresponding_text += text_array[current_index + 1]
        current_index += 1
        if '_' in text_array[current_index]:
            should_skip_next_lines_counter += 1

    # trimming text from starting ( and from ending ) and removing underscores
    corresponding_text = corresponding_text[1:len(corresponding_text) - 1].replace("_", "")

    return [should_skip_next_lines_counter, corresponding_text]


def search_current_line_and_above(text_array, index_array, index, underscore_in_line_index_array):
    corresponding_text_array = []
    should_skip_next_underscores_counter = 0
    current_line = text_array[index_array[index]]
    # which data has already been processed
    last_index_of_processed_info = 0

    for underscore_index in range(len(underscore_in_line_index_array)):
        if should_skip_next_underscores_counter > 0:
            should_skip_next_underscores_counter -= 1
            continue

        if len(underscore_in_line_index_array) == 1 \
                and len(current_line[underscore_in_line_index_array[underscore_index]:len(current_line)]) <= 2:
            return get_corresponding_text_from_left_and_above(
                text_array, index_array, index, underscore_in_line_index_array, underscore_index
            )

        date_data_option = check_for_date_data(current_line, underscore_index, underscore_in_line_index_array)
        should_skip_next_underscores_counter = date_data_option[0]

        if date_data_option[2] > 0:
            last_index_of_processed_info = date_data_option[2]

        if date_data_option[1]:
            corresponding_text_array.append(date_data_option[1])
        elif last_index_of_processed_info > underscore_in_line_index_array[underscore_index - 1]:
            text_option = current_line[
                          last_index_of_processed_info:underscore_in_line_index_array[underscore_index]].strip()
            corresponding_text_array.append(text_option)
        else:
            text_option = current_line[
                          underscore_in_line_index_array[underscore_index - 1]:underscore_in_line_index_array[
                              underscore_index]].strip()
            corresponding_text_array.append(text_option)

    return corresponding_text_array


def get_corresponding_text_from_left_and_above(
        text_array,
        index_array,
        index,
        underscore_in_line_index_array,
        underscore_index
):
    current_line = text_array[index_array[index]]
    text_to_the_left = current_line[0:underscore_in_line_index_array[underscore_index]]
    dot_indexes = find_indexes(text_to_the_left, '\.')
    dot_indexes.reverse()

    if dot_indexes:
        for dot_index in dot_indexes:
            if text_to_the_left[dot_index + 1].isupper():
                return text_to_the_left[dot_index + 1:underscore_in_line_index_array[underscore_index]]

    if text_to_the_left:
        if text_to_the_left[0].isupper() or text_to_the_left[0].isnumeric():
            return text_to_the_left.strip()
        else:
            return get_upper_lines_text(text_array, index_array[index]) + " " + text_to_the_left.strip()
    else:
        return get_upper_lines_text(text_array, index_array[index])


def get_upper_lines_text(text_array, index):
    upper_line = text_array[index - 1]
    dot_indexes_upper_line = find_indexes(upper_line, '\.')
    for dot_index in dot_indexes_upper_line:
        if upper_line[dot_index + 1].isupper():
            return upper_line[dot_index + 1:len(upper_line)]

    if upper_line[0].isupper() or upper_line[0].isnumeric():
        return upper_line

    return get_upper_lines_text(text_array, index - 1) + " " + upper_line.strip()


def check_for_date_data(current_line, underscore_index, underscore_in_line_index_array):
    should_skip_next_underscores_counter = 0
    date_data = ''
    last_index_of_processed_info = -1
    text_to_the_right = current_line[underscore_in_line_index_array[underscore_index]:len(current_line)]

    date_sign_indexes = find_indexes(text_to_the_right, "р\.")
    # print(text_to_the_right, date_sign_indexes and date_sign_indexes[0] <= 10)
    if date_sign_indexes and date_sign_indexes[0] <= 10:
        text_for_date = text_to_the_right[0:date_sign_indexes[0] + 2]
        last_index_of_processed_info = underscore_in_line_index_array[underscore_index] + date_sign_indexes[0] + 2
        should_skip_next_underscores_counter = len(find_indexes(text_for_date, "_")) - 1
        return [should_skip_next_underscores_counter, "дата", last_index_of_processed_info]

    date_sign_indexes = find_indexes(text_to_the_right, "року")

    if date_sign_indexes and date_sign_indexes[0] <= 12:
        text_for_date = text_to_the_right[0:date_sign_indexes[0] + 4]
        last_index_of_processed_info = underscore_in_line_index_array[underscore_index] + date_sign_indexes[0] + 4
        should_skip_next_underscores_counter = len(find_indexes(text_for_date, "_")) - 1
        return [should_skip_next_underscores_counter, "дата", last_index_of_processed_info]

    date_sign_indexes = find_indexes(text_to_the_right, "рік")

    if date_sign_indexes and date_sign_indexes[0] <= 10:
        text_for_date = text_to_the_right[0:date_sign_indexes[0] + 3]
        last_index_of_processed_info = underscore_in_line_index_array[underscore_index] + date_sign_indexes[0] + 3
        should_skip_next_underscores_counter = len(find_indexes(text_for_date, "_")) - 1
        return [should_skip_next_underscores_counter, "дата", last_index_of_processed_info]

    return [should_skip_next_underscores_counter, date_data, last_index_of_processed_info]


def find_properties_of_main_person_dictionary(data):
    found_properties = []

    for item in data:
        properties_in_item = find_properties_in_line(item)

        if properties_in_item:
            found_properties += properties_in_item

    return found_properties


def find_properties_in_line(item):
    properties = []

    for data in item.data_array:
        match = re.search("альтернативне ім'я", data.lower())
        if match:
            properties.append(["alternativeName", item.corresponding_line])
            continue

        match = re.search("прізвище, ім.я, по батькові", data.lower())
        if match:
            properties.append(["fullName", item.corresponding_line])
            continue

        # match = re.search("ім’я", data.lower())
        # flag = False
        # for property in properties:
        #     if property == "fullName":
        #         flag = True
        # flag = flag and match
        # if flag:
        #     properties.append(["birthName", item.corresponding_line])

        first_word_pos = -1
        second_word_pos = -1
        words_array = data.lower().split(" ")
        for i in range(len(words_array)):
            if first_word_pos == -1 and words_array[i] == "дата":
                first_word_pos = i
            if second_word_pos == -1 and words_array[i] == "народження":
                second_word_pos = i
        if first_word_pos != -1 and second_word_pos != -1 and second_word_pos - first_word_pos <= 3:
            properties.append(["dateOfBirth", item.corresponding_line])
            continue

        first_word_pos = -1
        second_word_pos = -1
        words_array = data.lower().split(" ")
        for i in range(len(words_array)):
            if first_word_pos == -1 and words_array[i] == "дата":
                first_word_pos = i
            if second_word_pos == -1 and words_array[i] == "смерті":
                second_word_pos = i
        if first_word_pos != -1 and second_word_pos != -1 and second_word_pos - first_word_pos <= 3:
            properties.append(["dateOfDeath", item.corresponding_line])
            continue

        match = re.search("прізвище", data.lower())
        flag = False
        for property in properties:
            if property == "fullName":
                flag = True
        flag = not flag and match
        if flag:
            properties.append(["familyName", item.corresponding_line])
            continue

        match = re.search("стать", data.lower())
        if match:
            properties.append(["gender", item.corresponding_line])
            continue

        match = re.search("ім’я", data.lower())
        flag = False
        for property in properties:
            if property == "fullName":
                flag = True
        flag = not flag and match
        if flag:
            properties.append(["givenName", item.corresponding_line])
            continue

        match = re.search("по матері", data.lower())
        if match:
            properties.append(["matronymicName", item.corresponding_line])
            continue

        match = re.search("по батькові", data.lower())
        flag = False
        for property in properties:
            if property == "fullName":
                flag = True
        flag = not flag and match
        if flag:
            properties.append(["patronymicName", item.corresponding_line])
            continue

    return properties


if __name__ == "__main__":
    app.run(port=3000, host="localhost")
