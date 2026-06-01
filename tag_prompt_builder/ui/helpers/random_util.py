# tag_prompt_builder/ui/helpers/random_util.py
import random
from collections import defaultdict
from typing import List
from tag_prompt_builder.models.tag_item import TagItem
from tag_prompt_builder.managers.tag_manager import TagManager

def perform_random_slot(slot_node, tag_manager: TagManager) -> List[TagItem]:
    config = slot_node.random_slot_config
    pool_name = config.get("pool_name")
    count = config.get("count", 1)
    allow_duplicates = config.get("allow_duplicates", False)

    if not pool_name or count <= 0:
        return []

    pool_tags = tag_manager.random_pool_manager.get_pool_tags(pool_name, tag_manager)
    if not pool_tags:
        return []

    group_map = defaultdict(list)
    individual_tags = []
    for tag in pool_tags:
        folder = tag.parent
        while folder and not folder.single_selection:
            folder = folder.parent
        if folder and folder.single_selection:
            gid = folder.full_id()
            group_map[gid].append(tag)
        else:
            individual_tags.append(tag)

    chosen = []
    if not allow_duplicates:
        for tags in group_map.values():
            chosen.append(random.choice(tags))
        remaining = count - len(chosen)
        if remaining > 0 and individual_tags:
            if remaining >= len(individual_tags):
                chosen.extend(individual_tags)
            else:
                chosen.extend(random.sample(individual_tags, remaining))
        return chosen[:count]
    else:
        for _ in range(count):
            available = list(pool_tags)
            for existing in chosen:
                folder = existing.parent
                while folder and not folder.single_selection:
                    folder = folder.parent
                if folder and folder.single_selection:
                    gid = folder.full_id()
                    available = [t for t in available if not _is_in_exclusive_group(t, gid)]
            if not available:
                break
            chosen.append(random.choice(available))
        return chosen

def _is_in_exclusive_group(tag: TagItem, group_id: str) -> bool:
    folder = tag.parent
    while folder and not folder.single_selection:
        folder = folder.parent
    return folder is not None and folder.single_selection and folder.full_id() == group_id