# managers/random_pool_manager.py
import json
import os
from tag_prompt_builder.app_config import DATA_DIR

RANDOM_POOLS_FILE = os.path.join(DATA_DIR, 'random_pools.json')

class RandomPoolManager:
    def __init__(self):
        self.pools = {}
        self.load()

    def load(self):
        if os.path.exists(RANDOM_POOLS_FILE):
            try:
                with open(RANDOM_POOLS_FILE, 'r', encoding='utf-8') as f:
                    self.pools = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.pools = {}
        else:
            self.pools = {}

    def save(self):
        try:
            with open(RANDOM_POOLS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.pools, f, ensure_ascii=False, indent=2)
        except IOError:
            pass  # 可加入日志

    def create_pool(self, name, description=""):
        if name not in self.pools:
            self.pools[name] = {'description': description, 'tags': []}
            self.save()

    def delete_pool(self, name):
        if name in self.pools:
            del self.pools[name]
            self.save()

    def add_tag_to_pool(self, pool_name, tag_full_id):
        if pool_name in self.pools and tag_full_id not in self.pools[pool_name]['tags']:
            self.pools[pool_name]['tags'].append(tag_full_id)
            self.save()

    def remove_tag_from_pool(self, pool_name, tag_full_id):
        if pool_name in self.pools and tag_full_id in self.pools[pool_name]['tags']:
            self.pools[pool_name]['tags'].remove(tag_full_id)
            self.save()

    def get_pool_tags(self, pool_name, tag_manager):
        tag_ids = self.pools.get(pool_name, {}).get('tags', [])
        tags = []
        for fid in tag_ids:
            tag = tag_manager.find_item_by_full_id(fid)
            if tag and not tag.is_folder:
                tags.append(tag)
        return tags

    def is_tag_in_any_pool(self, tag_full_id):
        for pool in self.pools.values():
            if tag_full_id in pool['tags']:
                return True
        return False

    def list_pool_names(self):
        return list(self.pools.keys())