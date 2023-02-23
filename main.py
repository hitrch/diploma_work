import pdfminer.high_level  # for reading pdf to string
import re  # for finding occurrences in string


def main():
    text = read_file()
    prepared_data_for_classification = corresponding_text_finding_algorithm(text)


def read_file():
    file = open('test-file.pdf', 'rb')
    return pdfminer.high_level.extract_text(file)


def corresponding_text_finding_algorithm(text):
    preprocessed_text_array = preprocess_text(text)
    return analyze_text(preprocessed_text_array)


def preprocess_text(text):
    text = remove_unnecessary_symbols(text, ["\r", "\t", "|"])
    text = remove_unnecessary_symbols_between_underscores(text)
    text = shrink_symbols(text, " ")
    text = shrink_symbols(text, "_")
    text = remove_spaces_in_first_place_of_row(text)
    text = remove_newline_if_empty_line(text)
    text = transform_string_to_array_based_on_newlines(text)
    return text


def remove_unnecessary_symbols(text, symbols_to_remove):
    for symbol in symbols_to_remove:
        text = text.replace(symbol, ' ')
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
            data.append(step_data[1])
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
    should_skip_next_underscores_counter = 0
    underscore_in_line_index_array = find_indexes(text_array[index_array[index]], '_')
    print(index, text_array[index_array[index]], text_array[index_array[index] + 1])

    if len(underscore_in_line_index_array) == 1:
        right_data = search_right(text_array, index_array, index)
        should_skip_next_lines_counter += right_data[0]
        corresponding_texts_array = right_data[2]
        return [should_skip_next_lines_counter, corresponding_texts_array]

    for underscore_index in underscore_in_line_index_array:
        if should_skip_next_underscores_counter > 0:
            should_skip_next_underscores_counter -= 1
            continue

        left_option = search_left(text_array, index_array, index, underscore_index)
        should_skip_next_underscores_counter = left_option[0]
        corresponding_texts_array.append(left_option[1])

    return [should_skip_next_lines_counter, corresponding_texts_array]


def search_right(text_array, index_array, index):
    should_skip_next_lines_counter = 0
    should_skip_next_underscores_counter = 0
    corresponding_text = ''

    if index < len(text_array) - 1:
        # in case corresponding text takes multiple rows we should consider it as one piece
        opening_brackets_count = len(find_indexes(text_array[index_array[index] + 1], "("))

        if opening_brackets_count:
            closing_brackets_count = len(find_indexes(text_array[index_array[index] + 1], ")"))

            if opening_brackets_count != closing_brackets_count:
                processed_data = process_lines_with_multiline_corresponding_text(
                    text_array, index_array, index, opening_brackets_count, closing_brackets_count
                )
                should_skip_next_lines_counter = processed_data[0]
                corresponding_text = processed_data[1]

    return [should_skip_next_lines_counter, should_skip_next_underscores_counter, corresponding_text]


def process_lines_with_multiline_corresponding_text(
        text_array,
        index_array,
        index,
        opening_brackets_count,
        closing_brackets_count
):
    increment = 1
    should_skip_next_lines_counter = 1
    corresponding_text = text_array[index_array[index] + 1]

    while opening_brackets_count != closing_brackets_count:
        opening_brackets_count += len(find_indexes(text_array[index_array[index] + increment + 1], "("))
        closing_brackets_count += len(find_indexes(text_array[index_array[index] + increment + 1], ")"))
        corresponding_text += text_array[index_array[index] + increment + 1]
        increment += 1
        if '_' in text_array[index_array[index] + increment + 1]:
            should_skip_next_lines_counter += 1

    # trimming text from starting ( and from ending ) and removing underscores
    corresponding_text = corresponding_text[1:len(corresponding_text) - 2].replace("_", "")
    return [should_skip_next_lines_counter, corresponding_text]


def search_left(text_array, index_array, index, underscore_index):
    corresponding_text = ''
    should_skip_next_underscores_counter = 0

    return [should_skip_next_underscores_counter, corresponding_text]


if __name__ == "__main__":
    main()
