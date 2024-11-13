import os


def clear_directory(directory):
    """
    清空文件夹下所有文件
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            # print(f"Deleted {file_path}")


def find_or_create_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)



def find_or_create_doc(file_path,type):
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if type == 'json':
            with open(file_path, 'w') as file:
                # 在新创建的文件中写入初始内容
                file.write('[]')
        if type == 'txt':
            with open(file_path, 'w') as file:
                # 在新创建的文件中写入初始内容
                file.write('')




if __name__ == '__main__':

    organization = '某' # 替换为实际的组织名称
    file_path = f'各组织历史通知/待发送/{organization}学院待发送.json'
    find_or_create_doc(file_path,'json')
    file_path = f'各组织历史通知/待发送/{organization}学院待发送.txt'
    find_or_create_doc(file_path,'txt')