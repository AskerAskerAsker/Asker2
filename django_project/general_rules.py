'''
 Variáveis que definem regras gerais para uso do site.
 Por favor, fazer o possível para modificar as regras apenas por este arquivo,
 caso a regra exista aqui.
 
 Ao adicionar uma nova variável de regra neste arquivo,
 talvez seja importante criar uma função que retorna essa variável
 no main_app_extras.py para que essa variável possa ser usada em templates.
'''

MINIMUM_POINTS_FOR_POSTING_IMAGES = 100
MAXIMUM_POLL_CHOICES = 12
SECONDS_TO_CHOOSE_BEST_ANSWER = 3600
ALLOWED_IP_TYPES = 'ABR'
MAXIMUM_SILENCED_USERS = 300
MAXIMUM_BLOCKED_USERS = 300
CONFIRMATION_CODE_LENGTH = 100
RECOVER_PW_CODE_LENGTH = 120

if CONFIRMATION_CODE_LENGTH == RECOVER_PW_CODE_LENGTH:
    raise ValueError('general_rules.py: os códigos de confirmação de e-mail e de recuperação de senha devem ter tamanho diferente')