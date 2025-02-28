from common.pubsub_queue import PubSubMessage
from extra.parsers.parser import Parser


def deserialize_message(serialized_msg):
    return PubSubMessage.deserialize(serialized_msg)


def get_input_data_for_review(input_type, input):
    if input_type == "colab_url":
        parser_ins = Parser()
        return parser_ins.notebook_parser(input["raw_content"])
    else:
        return input
