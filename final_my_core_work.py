from pprint import pprint
from datetime import datetime
import vk_api
from vk_api.exceptions import ApiError
from queue import Queue
import time
from final_config import acces_token, comunity_token


class VkTools:
    def __init__(self, acces_token):
        self.vkapi = vk_api.VkApi(token=acces_token)
        self.vkapi_community = vk_api.VkApi(token=comunity_token)
        self.responses = Queue()

    def send_message(self, user_id, message):
        try:
            # используйте self.vkapi_user.method для отправки сообщений от имени пользователя
            # и self.vkapi_community.method для отправки сообщений от имени сообщества
            self.vkapi_community.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': 0})
        except ApiError as e:
            print(f'Ошибка при отправке сообщения: {e}')

    def _bdate_toyear(self, bdate):
        user_year = bdate.split('.')[2]
        now = datetime.now().year
        return now - int(user_year)

    def process_message(self, event):
        self.responses.put(event.text)

    def send_message_and_wait_for_reply(self, user_id, message):
        self.send_message(user_id, message)
        timeout = 100  # 30 seconds (0.1 * 300)
        while timeout > 0:
            time.sleep(0.1)  # wait for reply
            timeout -= 1
            try:
                incoming_message = self.vkapi_community.method('messages.getConversations',
                                                               {'offset': 0, 'count': 20, 'filter': 'unread'})
                if incoming_message['count'] > 0:
                    for item in incoming_message['items']:
                        if item['last_message']['from_id'] == user_id:
                            reply = item['last_message']['text']
                            return reply
            except ApiError as e:
                print(f'Ошибка при получении сообщения: {e}')

        print("Timeout waiting for user's response")
        return None

    def get_name(self, user_id):
        try:
            info, = self.vkapi.method('users.get', {'user_id': user_id, })
        except ApiError:
            info = {}
            print(f'У нас тут косяк со стороны АПИ')

        result = {
            'name': (info['first_name'] + ' ' + info[
                'last_name']) if 'first_name' in info and 'last_name' in info else None, }

        return result

    def get_profile_info(self, user_id):
        try:
            info, = self.vkapi.method('users.get', {'user_id': user_id, 'fields': 'city,sex,bdate,relation'})
        except ApiError:
            info = {}
            print(f'У нас тут косяк со стороны АПИ')

        result = {
            'name': (info['first_name'] + ' ' + info[
                'last_name']) if 'first_name' in info and 'last_name' in info else None,
            'sex': info.get('sex'),
            'city': info.get('city')['title'] if info.get('city') is not None else None,
            'year': self._bdate_toyear(info.get('bdate')) if info.get('bdate') else None,
            'relation': info.get('relation')
        }

        if result['city'] is None:
            result['city'] = self.send_message_and_wait_for_reply(user_id,
                                                                  ' Из какого ты города? ')
        if result['sex'] is None:
            result['sex'] = self.send_message_and_wait_for_reply(user_id,
                                                                 'Кто вы? (1 - Девушка, 2 - Молодой человек): ')
        if result['year'] is None:
            result['year'] = self.send_message_and_wait_for_reply(user_id,
                                                                  'Дата рождения ваша в формате день.месяц.год: ')
        if result['relation'] is None:
            result['relation'] = self.send_message_and_wait_for_reply(user_id, 'Как у вас с семейным положением?: ')

        return result

        # ну и возвращаем результат который выше определён , чтобы была только нужная информация

    def search_worksheet(self, params, offset):
        try:
            users = self.vkapi.method('users.search',
                                      {
                                          'count': 50,
                                          'offset': offset,
                                          'hometown': params['city'],
                                          'sex': 1 if params['sex'] == 2 else 2,
                                          'has_photo': True,
                                          'age_from': params['year'] - 10,

                                          'age_to': params['year'] + 3,
                                      })


        except ApiError:
            users = []
            print(f'У нас тут косяк со стороны АПИ')

        result = [{
            'name': item['first_name'] + ' ' + item['last_name'],
            'id': item['id']
        } for item in users['items'] if item['is_closed'] is False
        ]

        return result
        ''' а теперь добавим к этому делу метод как искафть фото'''

    def get_photos(self, id):
        try:
            photos = self.vkapi.method('photos.get',
                                       {'owner_id': id,
                                        'album_id': 'profile',
                                        'extended': 1}
                                       # этот параметр показывает какая
                                       # дополнительная информация по фотографиям нам требуется. 1 - означает, что
                                       # необходима вся инфо о фото, такая кодировка в документации)
                                       )
        except ApiError:
            photos = {}
            print(f'Лажа с фотками')

        '''Создается списко чтобы не показываеть всю информацию о фото, а только нужную,
        в данном случае это количество лайков и соответсвенно функция будет возвращать
        result'''

        result = [{'owner_id': item['owner_id'],  # это id профиля пользователя
                   'id': item['id'],  # а это id фотографии , он у каждой фото свой
                   'likes': item['likes']['count'],
                   'comments': item['comments']['count']
                   } for item in photos['items']
                  ]
        ''' Сюда надо добавить сортировку по лайка и комментам от большого к меньшему'''
        # Сортируем все фотографии по количеству лайков в порядке убывания
        sorted_photos = sorted(result, key=lambda x: x['likes'], reverse=True)

        # Возвращаем три фотографии с наибольшим количеством лайков
        return sorted_photos[:3]


if __name__ == '__main__':
    user_id = 1456975  # this is my user_id from VK
    tools = VkTools(acces_token)
    params = tools.get_profile_info(user_id)  # получили параметры пользователя
    worksheets = tools.search_worksheet(params,
                                        3)  # ищем с помощью воркщитов по входным параметра пользователя, полученным ранее
    worksheet = worksheets.pop()  # принцип работы метода pop. Он берёт последний элемент из списка
    # добавляет его в переменную, но при этом удаляет его из списка.И список уже выводится
    # без неё

    photos = tools.get_photos(worksheet['id'])
    pprint(params)
    pprint(worksheets)
    pprint(worksheet)
    pprint(photos)

    print(worksheet['id'])
