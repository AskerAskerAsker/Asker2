# Script para criação de páginas estáticas de erro para serem servidas pelo nginx, django, etc.
        
style_location = 'https://asker.fun/static/css/nginx_err.css'

err_msgs = {400: ("Pedido inválido", "Erro 400 - Você pode voltar retorne à página inicial do Asker."),
            401: ("Autenticação não concluída", "Erro 401 - Você pode voltar retorne à página inicial do Asker."),
            403: ("Acesso negado", "Erro 403 - O Asker concluiu que você não possui acesso a esta página."),
            404: ("Esta página não existe", "Erro 404 - Você pode voltar à página inicial do Asker."), 
            408: ("Tempo excedido", "Erro 408 - Você pode voltar à página inicial do Asker."),
            500: ("Pedido inesperado", "Erro 500 - Você pode voltar à página inicial do Asker."),
            502: ("Por favor, aguarde", "O Asker está sendo atualizado e retornará em breve."),
            503: ("Recurso indisponível", "Por favor, tente novamente ou volte à página inicial do Asker."),
            504: ("Tempo limite excedido", "Por favor, tente novamente ou volte à página inicial do Asker.")
           }
   
with open('base.html', 'r', encoding='utf-8') as f:
    doc = f.read()
    
for err in err_msgs:
    n_doc = doc.replace('{{ err_msg }}', err_msgs[err][1])
    n_doc = n_doc.replace('{{ err_title }}', err_msgs[err][0])
    n_doc = n_doc.replace('{{ style_location }}', style_location)
    
    with open('{}.html'.format(str(err)), 'w', encoding='utf-8') as f:
        f.write(n_doc)
        
    print('Escrito:', err, err_msgs[err][0])
