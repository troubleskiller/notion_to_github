from notion_client import Client
from notion2md.exporter.block import MarkdownExporter, StringExporter

notion_token = 'secret_K9rEXfR0TCyXTMB8w0EhRkXUAnSwtmtm29J4hSyAWtY'
notion_database_id = 'cfa914c2-9107-4f73-bc94-015cbe56961a'


def main():
    MarkdownExporter(output_filename='test', token=notion_token, block_id='31619ea1-3fdc-4ae5-8fe7-4ee4114b7bb2',
                     output_path='./posts', download=True, unzipped=True).export()


if __name__ == '__main__':
    main()
