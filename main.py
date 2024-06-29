import os
from notion_client import Client
from notion2md.exporter.block import MarkdownExporter, StringExporter
import yaml
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.addHandler(logging.StreamHandler())


class Notion:
    def __init__(self, token, database_id):
        self.notion = Client(auth=token)
        self.database_id = database_id

    def get_page_id(self, data: dict) -> list:
        rich_text_node = data['properties'].get('Article', {})
        mentions = []
        if rich_text_node['type'] != 'rich_text':
            raise TypeError("this field is not a rich text")
        for i in rich_text_node['rich_text']:
            if i['type'] == 'mention':
                mentions.append(i['mention']['page']['id'])
        return mentions[0] if len(mentions) > 0 else None

    def title(self, data: dict) -> str:
        title_node = data['properties'].get('Name', {})
        title = ''
        if title_node['type'] != 'title':
            raise TypeError("this field is not a title")
        for i in title_node['title']:
            title += i['plain_text']
        return title

    def is_publish(self, data: dict) -> bool:
        return data['properties'].get('IsPublish', {}).get('checkbox', False)

    def need_update(self, data: dict) -> bool:
        return data['properties'].get('NeedUpdate', {}).get('checkbox', False)

    def md_filename(self, data: dict) -> str:
        rich_text_node = data['properties'].get('MDFilename', {})
        file_name = ''
        if rich_text_node['type'] != 'rich_text':
            raise TypeError("this field is not a rich text")
        for i in rich_text_node['rich_text']:
            file_name += i['plain_text']
        return file_name

    def category(self, data: dict) -> str:
        return data['properties'].get('Category', {}).get('select', {}).get('name', '')

    def tags(self, data: dict) -> list:
        tags_ = []
        tags_node = data['properties'].get('Tags', {}).get('multi_select', [])
        for i in tags_node:
            tags_.append(i['name'])
        return tags_

    def create_at(self, data: dict) -> str:
        return data['properties'].get('CreateAt', {}).get('created_time', '')

    def update_at(self, data: dict) -> str:
        return data['properties'].get('UpdateAt', {}).get('last_edited_time', '')

    def publish(self, data: dict) -> bool:
        page_id = data['id']
        self.notion.pages.update(page_id, properties={
            "IsPublish": {"checkbox": True},
            "NeedUpdate": {"checkbox": False}
        })

    def items_changed(self):
        '''获取需要更改的项'''
        data = self.notion.databases.query(database_id=self.database_id, filter={
            "or": [
                {
                    "property": "IsPublish",
                    "checkbox": {
                        "equals": False,
                    },
                },
                {
                    "property": "NeedUpdate",
                    "checkbox": {
                        "equals": True,
                    },
                },
            ]
        })
        return data.get('results') or []


def get_markdown_with_yaml_header(page_node: dict, article_content: str, notion: Notion):
    yaml_header = {
        'title': notion.title(page_node),
        'date': notion.create_at(page_node),
        'showToc': True,
        'tags': notion.tags(page_node),
        'categories': [notion.category(page_node), ],
    }
    header_text = yaml.dump(yaml_header, allow_unicode=True)
    return f'---\n{header_text}\n---\n\n\n\n{article_content}'


def save_markdown_file(path_prefix: str, content: str, filename: str):
    filename = filename.strip()
    filename = filename if filename.endswith('.md') else f'{filename}.md'
    logger.info(f'save markdwon file to {os.path.join(os.getcwd(), path_prefix, filename)}')
    if not os.path.exists(path_prefix):
        os.makedirs(path_prefix)
    md_filepath = os.path.join(os.getcwd(), path_prefix, filename)
    with open(md_filepath, 'w+', encoding='utf-8') as f:
        f.write(content)


def github_action_env(key):
    return f'INPUT_{key}'.upper()


def main():
    # notion_token = os.environ[github_action_env('NOTION_TOKEN')]
    # notion_database_id = os.environ[github_action_env('NOTION_DATABASE_ID')]
    notion_token = 'secret_K9rEXfR0TCyXTMB8w0EhRkXUAnSwtmtm29J4hSyAWtY'
    notion_database_id = 'cfa914c2-9107-4f73-bc94-015cbe56961a'
    md_store_path_prefix = os.getenv(github_action_env('MD_STORE_PATH_PREFIX')) or 'content/posts'  # 保存markdown文件的目录
    notion = Notion(notion_token, notion_database_id)
    page_nodes = notion.items_changed()
    logger.info(f'it will update {len(page_nodes)} article...')
    for page_node in page_nodes:
        if not notion.title(page_node).strip():
            continue
        logger.info(f'get page content from notion...')
        page_id = notion.get_page_id(page_node)
        # 将page转化为markdown
        logger.info(f'parse <<{notion.title(page_node)}>>...')
        markdown_text = StringExporter(output_filename=notion.md_filename(page_node), token=notion_token,
                                       block_id=page_id.__str__(),
                                       output_path='./content/posts', download=True, unzipped=True).export()
        markdown_with_header = get_markdown_with_yaml_header(page_node, markdown_text, notion)
        # # 保存markdown到指定目录
        save_markdown_file(md_store_path_prefix, markdown_with_header, notion.md_filename(page_node))
        # # 更新notion中的对应项
        logger.info('update page property for article <<{notion.title(page_node)}>>...')
        notion.publish(page_node)
    logger.info('all done!!!')


if __name__ == '__main__':
    logger.info('start parse notion for blog...')
    main()
