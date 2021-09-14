#!/usr/bin/python
# -*- coding: utf-8 -*-

import heapq
import random
import gettext
import math

def traduzArgparse(s):

    dicionario = {
        'positional arguments':'Argumentos posicionais',
        'optional arguments':'Argumentos opcionais',
        'show this help message and exit':'exibe essa ajuda e sai',
        'usage: ':'Uso: '}

    if s in dicionario:
        s = dicionario[s]

    return s

gettext.gettext = traduzArgparse

import argparse

# Parâmetros do protocolo de acesso ao meio (se algum)
###
##
# TODO: se o protocolo de acesso ao meio implementado tiver algum parâmetro (por
# exemplo, o tamanho da janela de backoff), declare-o aqui como uma constante.

# Classe escalonador
class Escalonador:

    def __init__(self, duracao = 10):
        self.duracao = duracao

        # Heap para armazenar os eventos
        self.eventos = []

        # Tempo atual interno do escalonador
        self.agora = 0

        # Número de sequência para os eventos agendados.
        self.seq = 0

    # Agenda um novo evento para o tempo t. Quando o evento for disparado,
    # a função callback será chamada com dado como argumento.
    def agendaEvento(self, t, callback, dado):

        #print "Agendando evento para t = {0} com callback {1} e dado {2}".format(t, callback, dado)

        ev = (callback, dado)
        heapq.heappush(self.eventos, (t, self.seq, ev))
        self.seq = self.seq + 1

    # Retorna o tempo atual, i.e., tempo do último evento disparado.
    def getAgora(self):
        return self.agora

    # Método principal da classe: consome os eventos, disparando-os
    # até que a lista de eventos fique vazia ou até que a duração da simulação
    # seja alcançada.
    def executa(self):

        while(len(self.eventos) and self.agora < self.duracao):

            # Obtém próximo evento da lista atualiza tempo atual
            ev = heapq.heappop(self.eventos)
            self.agora = ev[0]
            ev = ev[2]

            # Dispara a callback do evento, passando como argumentos o 
            # dado do evento.
            cb = ev[0]
            dado = ev[1]
            if dado != None:
                cb(dado)
            else:
                cb()

# Classe pacote (para guardar estado)
class Pacote:

    def __init__(self):
        self.estado = {}

    def setEstado(self, chave, valor):

        self.estado[chave] = valor

    def getEstado(self, chave):

        if chave in self.estado:
            return self.estado[chave]
        else:
            return None
    
# Classe interface
class Interface:

    def __init__(self, no, barramento, escalonador, taxaDeTransmissao = 1e8):

        # Referências para outros objetos
        self.no = no
        self.barramento = barramento
        self.escalonador = escalonador

        # Fila de pacotes a serem transmitidos.
        self.fila = []

        # Lista dos pacotes cujo sinal está sendo recebido agora pela interface.
        self.sinaisRecebidos = []

        # Armazena o pacote atualmente em transmissão (se algum)
        self.pacoteAtual = None 

        # Taxa de transmissão (em b/s)
        self.taxaDeTransmissao = taxaDeTransmissao

        # Dicionário para armazenar estatísticas sobre os pacotes que passam pela interface.
        self.estatisticas = {'perdasPorColisao': 0, 
                                'pacotesRecebidos': 0,
                                'atrasoTotal': 0.0,
                                'tempoUtilTotal': 0.0,
                                'bytesRecebidos': 0}

    # Método que imprime um sumário das estatísticas de desempenho coletadas.
    def sumarizaEstatisticas(self):

        print("Total de pacotes perdidos por colisão: {}".format(self.estatisticas['perdasPorColisao']))
        print("Total de pacotes recebidos com sucesso: {}".format(self.estatisticas['pacotesRecebidos']))

        if self.estatisticas['perdasPorColisao'] + self.estatisticas['pacotesRecebidos'] > 0:
            print("Taxa de perda de pacotes por colisão: {:.6}%".format(
                100.0 * self.estatisticas['perdasPorColisao'] / (self.estatisticas['perdasPorColisao'] + self.estatisticas['pacotesRecebidos'])))
        else:
            print("Taxa de perda de pacotes por colisão: N/A")

        print("Tempo total de uso do enlace com transmissões bem sucedidas: {}".format(self.estatisticas['tempoUtilTotal']))
        print("Utilização do meio: {:.6%}".format(self.estatisticas['tempoUtilTotal'] / self.escalonador.getAgora()))

        print("Vazão: {:.2f} b/s".format(self.estatisticas['bytesRecebidos'] * 8.0 / self.escalonador.getAgora()))

        if self.estatisticas['pacotesRecebidos'] > 0:
            print("Atraso médio (da geração à entrega bem-sucedida): {:.2f} ms".format(self.estatisticas['atrasoTotal'] * 1000.0 / self.estatisticas['pacotesRecebidos']))
        else:
            print("Atraso médio (da geração à entrega bem-sucedida): N/A")

    # Método chamado pelo meio de transmissão para indicar que começamos
    # a receber o sinal de um novo transmissor.
    def adicionaSinalRecebido(self, p):

        # Adiciona o pacote à lista de pacotes recebidos.
        self.sinaisRecebidos.append(p)

        # Se já havia pacotes na lista, marcar que houve uma colisão
        if len(self.sinaisRecebidos) > 1:

            for pi in self.sinaisRecebidos:
                pi.setEstado('colisao' + str(self.no.id), 1)

    # Método chamado pelo meio de transmissão para indicar que terminamos
    # de receber o sinal de um novo transmissor.
    def removeSinalRecebido(self, p):

        # Adiciona o pacote à lista de pacotes recebidos.
        self.sinaisRecebidos.remove(p)

        # Pacote é destinado ao nó local?
        if p.getEstado('destino') == self.no.id:

            # Pacote foi recebido sem colisão?
            if p.getEstado('colisao' + str(self.no.id)) != 1:

                #print("t = {0:.9f}, nó {1}: pacote no. {2} do nó {3} recebido".format(self.escalonador.getAgora(), self.no.id, p.getEstado('numeroDeSequencia'), p.getEstado('origem')))
                p.setEstado('statusDeRecepcao', 1)

                # Anotar nas estatísticas
                self.estatisticas['pacotesRecebidos'] = self.estatisticas['pacotesRecebidos'] + 1
                self.estatisticas['tempoUtilTotal'] = self.estatisticas['tempoUtilTotal'] + p.getEstado('ttrans')
                self.estatisticas['bytesRecebidos'] = self.estatisticas['bytesRecebidos'] + p.getEstado('tamanho')
                self.estatisticas['atrasoTotal'] = self.estatisticas['atrasoTotal'] + (self.escalonador.getAgora() - p.getEstado('timestamp'))
            else:
                #print("t = {0:.9f}, nó {1}: pacote no. {2} do nó {3} sofreu colisao                                                   | COLISAO |".format(self.escalonador.getAgora(), self.no.id, p.getEstado('numeroDeSequencia'), p.getEstado('origem')))
                p.setEstado('statusDeRecepcao', 0)

                # Anotar nas estatísticas
                self.estatisticas['perdasPorColisao'] = self.estatisticas['perdasPorColisao'] + 1

            # Avisar à interface transmissora sobre o status da recepção.
            self.escalonador.agendaEvento(self.escalonador.getAgora(), p.getEstado('interfaceTransmissora').transmitePacote, None)

    # Adiciona um pacote ao final da fila de transmissão
    def enfileiraPacote(self, p):

        # Verifica se a fila está cheia
        if len(self.fila) < 10:

            # Há algum pacote atualmente em transmissão?
            if self.pacoteAtual == None:

                self.pacoteAtual = p
                self.transmitePacote()
            else:
                self.fila.insert(0, p)

    # Método que lida com a transmissão de um pacote. Ele é chamado várias vezes
    # ao longo desse processo (por exemplo, no início do processo, depois que a 
    # tentativa de transmissão termina).
    def transmitePacote(self):

        # Essa execução desse método é a primeira para esse pacote? Ou o método
        # está sendo chamado porque a última tentiva de retransmissão terminou?
        statusDeRecepcao = self.pacoteAtual.getEstado('statusDeRecepcao')

        #print "t = {0}: Executando transmitePacote no no {1} com n. de seq. {2} e statusDeRecepcao {3}".format(self.escalonador.getAgora(), self, self.pacoteAtual.getEstado('numeroDeSequencia'), statusDeRecepcao)

        if statusDeRecepcao == None:

            # Primeira tentativa de transmissão desse pacote. Delegar decisão do que
            # fazer ao método de acesso ao meio
            self.MACInicializa(self.pacoteAtual)

        elif statusDeRecepcao == 1:

            # Pacote já foi transmitido anteriormente e foi recebido com sucesso.
            # Transmissão desse pacote acabou. Avisar ao protocolo MAC dessa finalização.
            self.MACFinalizaTentativaDeTransmissaoBemSucedida(self.pacoteAtual)

            # Manipular a fila de pacotes para verificar o que fazer em seguida
            self.pacoteAtual = None

            # Há outros pacotes em fila?
            if len(self.fila) > 0:

                # Sim. Iniciar a transmissão.
                self.pacoteAtual = self.fila.pop()
                self.transmitePacote()
        else:

            # Pacote já foi transmitido anteriormente, mas colidiu. Retransmitir.
            # Delegar ao protocolo MAC a decisão do que fazer agora.
            self.MACFinalizaTentativaDeTransmissaoMalSucedida(self.pacoteAtual)

    # Método que verifica se o meio está livre. Retorna True se sim ou False se não.
    def MACVerificaMeioLivre(self):

        if len(self.sinaisRecebidos) > 0:
            return False
        else:
            return True

    # Método que pode ser chamado durante o processo de transmissão de um pacote para
    # realizar um backoff por um período determinado (parâmetro duracao, especificado
    # em segundos).
    def MACExecutaBackoff(self, duracao):

        #print("t = {0:.9f}, nó {1}: Entrando em backoff por {2} segundos                                               | BACKOFF |".format(self.escalonador.getAgora(), self.no.getId(), duracao))
        self.escalonador.agendaEvento(self.escalonador.getAgora() + duracao, self.MACFinalizaBackoff, self.pacoteAtual)

    # Método que pode ser chamado durante o processo de transmissão de um pacote para
    # realizar uma tentativa de transmissão pelo meio físico. O parâmetro p indica o 
    # pacote a ser transmitido.
    def MACTransmitePacote(self, p):

        #print("t = {0:.9f}, nó {1}: Iniciando transmissão do pacote {2} pelo barramento".format(self.escalonador.getAgora(), self.no.getId(), self.pacoteAtual.getEstado('numeroDeSequencia')))

        # Colocar no pacote uma referência para essa interface para que o receptor
        # possa nos alertar se a recepção foi correta ou não.
        self.pacoteAtual.setEstado('interfaceTransmissora', self)

        # Resetar o status de recepção a ser preenchido pelo receptor.
        self.pacoteAtual.setEstado('statusDeRecepcao', -1)
        
        # Resetar o status de colisão do pacote em relação ao receptor
        self.pacoteAtual.setEstado('colisao' + str(self.pacoteAtual.getEstado('destino')), 0)

        # Calcular o tempo de transmissão necessário para o pacote.
        ttrans = self.pacoteAtual.getEstado('tamanho') * 8 / self.taxaDeTransmissao
        self.pacoteAtual.setEstado('ttrans', ttrans)

        # Passar o pacote para o meio de transmissão
        self.barramento.propagaSinal(self, self.pacoteAtual, ttrans)


    #####
    ##
    # TODO: os quatro próximos métodos devem implementar a lógica do protocolo de 
    # acesso ao meio. Nesse template, eles contém apenas código para imprimir os
    # respectivos eventos na tela. A ideia é complementar cada um desses quatro métodos 
    # de forma a implementar o procedimento realizado pelo protocolo de acesso ao meio
    # em cada uma das quatro situações. 
    # 
    # Para isso, esses quatro métodos devem fazer uso dos métodos auxiliares 
    # MACTransmitePacote e MACExecutaBackoff, definidos acima. O primeiro realiza a 
    # transmissão do pacote pelo meio físico. Ao final dessa transmissão, dependendo
    # do resultado (sucesso ou colisão), um dos dois métodos abaixo, 
    # MACFinalizaTentativaDeTransmissaoMalSucedida ou 
    # MACFinalizaTentativaDeTransmissaoBemSucedida, é chamado.
    # Já o o método MACExecutaBackoff faz com que a interface aguarde um tempo antes
    # de reavaliar se deve ou não acessar o meio. Após o tempo de backoff especificado,
    # o método MACFinalizaBackoff abaixo é chamado.

    # Método que é chamado quando o processo de transmissão de um pacote é iniciado.
    # Ou seja, quando o pacote recém-chegado da camada de rede termina de ser preparado 
    # pela camada de enlace para transmissão. A lógica do protocolo de acesso ao meio
    # começa aqui.
    #
    # O único parâmetro do método, denominado p, é o pacote a ser transmitido.
    def MACInicializa(self, p):

        #print("t = {0:.9f}, nó {1}: Iniciando protocolo MAC para o pacote {2}".format(self.escalonador.getAgora(), self.no.getId(), self.pacoteAtual.getEstado('numeroDeSequencia')))

        # TODO
        self.MACTransmitePacote(p) 

    # Método que é chamado quando o último período de backoff realizado (iniciado 
    # pelo método MACExecutaBackoff) é finalizado. Cabe a esse método decidir o que 
    # fazer a seguir (se alguma coisa).
    #
    # O único parâmetro do método, denominado p, é o pacote a ser transmitido.
    def MACFinalizaBackoff(self, p):

        #print("t = {0:.9f}, nó {1}: Finalizando período de backoff para o pacote {2}".format(self.escalonador.getAgora(), self.no.getId(), self.pacoteAtual.getEstado('numeroDeSequencia')))

        # TODO
        pass

    # Método que é chamado quando a última tentativa de transmissão realizada (iniciada 
    # pelo método MACTransmitePacote) é finalizada com colisão. Cabe a esse
    # método decidir o que fazer a seguir (se alguma coisa).
    #
    # O único parâmetro do método, denominado p, é o pacote a ser transmitido.
    def MACFinalizaTentativaDeTransmissaoMalSucedida(self, p):

        #print("t = {0:.9f}, nó {1}: Finalizando tentativa de transmissao mal sucedida para o pacote {2}".format(self.escalonador.getAgora(), self.no.getId(), self.pacoteAtual.getEstado('numeroDeSequencia')))

        # TODO
        self.MACTransmitePacote(p)
        

    # Método que é chamado quando a última tentativa de transmissão realizada (iniciada 
    # pelo método MACTransmitePacote) é finalizada com sucesso. Cabe a esse
    # método decidir o que fazer a seguir (se alguma coisa).
    #
    # O único parâmetro do método, denominado p, é o pacote a ser transmitido.
    def MACFinalizaTentativaDeTransmissaoBemSucedida(self, p):

        #print("t = {0:.9f}, nó {1}: Finalizando tentativa de transmissao bem sucedida para o pacote {2}".format(self.escalonador.getAgora(), self.no.getId(), self.pacoteAtual.getEstado('numeroDeSequencia')))

        # TODO
        pass

# Classe meio de transmissão. Representa um barramento.
class MeioTransmissao:

    def __init__(self, escalonador):

        self.escalonador = escalonador

        # Lista de interfaces conectadas ao meio de transmissão
        # Cada entrada é uma tupla contendo um objeto da classe interface (
        # a interface em si) e um número denotando a distância do ponto
        # onde a interface está conectada até uma das pontas do barramento.
        self.conectores = []

    # Conecta uma nova interface ao barramento, a uma distância especificada
    # de uma das pontas do cabo. 
    def conectaInterface(self, interface, distancia):

        self.conectores.append((interface, distancia))

    # Busca por uma interface e retorna seu ponto de conexão
    def buscaConector(self, interface):

        for c in self.conectores:

            if c[0] == interface:
                return c[1]

        return None

    # Inicia a propagação do sinal do pacote p a partir da interface especificada
    # até as demais interfaces. Também agenda o final do recebimento do sinal, de
    # acordo com o tempo de transmissão (ttrans) especificado.
    def propagaSinal(self, interface, p, ttrans):

        # Determinar ponto de interconexão da interface transmissora para cálculo
        # do tempo de propagação.
        distTransmissor = self.buscaConector(interface)

        # Iterar pelas várias interfaces.
        for c in self.conectores:

            interfaceReceptor = c[0]
            distReceptor = c[1]

            # Calcular o atraso de propagação
            tprop = (distTransmissor - distReceptor) / 2e8
            if tprop < 0:
                tprop = -tprop

            # Escalonar o evento da chegada do sinal transmitido a essa interface
            self.escalonador.agendaEvento(self.escalonador.getAgora() + tprop, interfaceReceptor.adicionaSinalRecebido, p)

            # Escalonar o evento da finalização do sinal transmitido a essa interface
            self.escalonador.agendaEvento(self.escalonador.getAgora() + tprop + ttrans, interfaceReceptor.removeSinalRecebido, p)

# Classe nó (para gerar tráfego)
class No:

    def __init__(self, barramento, escalonador, id, intervaloEntrePacotes=1, destino=None, tamanhoDePacote=1500, taxaDeTransmissao=1e8):

        # Criar uma interface para o nó
        self.interface = Interface(self, barramento, escalonador, taxaDeTransmissao)

        # Número de sequência do próximo pacote gerado por esse nó.
        self.numeroDeSequencia = 0

        # Armazenar referências a outros objetos relevantes
        self.escalonador = escalonador

        # Id interno do nó
        self.id = id

        # Intervalo entre pacotes gerados por esse nó em segundos
        self.intervaloEntrePacotes = intervaloEntrePacotes

        # Destinatário dos pacotes gerados por esse nó. Um valor 'None' indica 
        # que esse nó não deverá transmitir pacotes.
        self.destino = destino

        # Tamanho dos pacotes transmitidos por esse nó (em bytes)
        self.tamanhoDePacote = tamanhoDePacote

        # Taxa de transmissão desse nó (em b/s)
        self.taxaDeTransmissao = taxaDeTransmissao

        # Temos um destinatário especificado?
        if self.destino != None:

            # Sortear um tempo aleatório até a geração do próximo pacote
            inter = random.expovariate(1.0 / self.intervaloEntrePacotes)

            # Agendar geração do primeiro pacote
            self.escalonador.agendaEvento(self.escalonador.getAgora() + inter, self.geraPacote, None)

    # Retorna o id do nó
    def getId(self):

        return self.id

    # Retorna a interface do nó
    def getInterface(self):

        return self.interface

    # Método chamado toda vez que o nó gera um novo pacote.
    def geraPacote(self):

        # Criar um novo pacote
        p = Pacote()
        p.setEstado('origem', self.id)
        p.setEstado('destino', self.destino)
        p.setEstado('numeroDeSequencia', self.numeroDeSequencia)
        p.setEstado('tamanho', self.tamanhoDePacote)
        p.setEstado('timestamp', self.escalonador.getAgora())

        # Incrementar o número de sequência
        self.numeroDeSequencia = self.numeroDeSequencia + 1

        # Enfileirar o pacote para transmissão
        self.interface.enfileiraPacote(p)

        # Sortear um tempo aleatório até a geração do próximo pacote
        inter = random.expovariate(1.0 / self.intervaloEntrePacotes)

        # Agendar geração do primeiro pacote
        self.escalonador.agendaEvento(self.escalonador.getAgora() + inter, self.geraPacote, None)

def leArgumentos():

    # Criar um parser para as opções de linha de comando.
    parser = argparse.ArgumentParser(description='Simulador de protocolo MAC.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('pos', type=float, default=[50, 0, 100], nargs='*',
                        help='posição do nó no barramento (m). Primeiro nó é o receptor.')
    parser.add_argument('-r', type=float, default=1e5,
                        help='taxa de transmissão das interfaces (b/s)')
    parser.add_argument('-s', type=int, default=1500,
                        help='tamanho dos pacotes (B)')
    parser.add_argument('-i', type=float, default=0.05,
                        help='intervalo de geração de pacotes para cada transmissor (s)')
    parser.add_argument('-t', type=float, default=1000,
                        help='duração da simulação (s)')

    args = parser.parse_args()

    return args

# Função principal que encapsula execução
def main():

    # Lê argumentos da linha de comando
    args = leArgumentos()

    # Inicializa gerador de números pseudo-aleatórios
    random.seed()

    # Criar o escalonador de eventos
    escalonador = Escalonador(args.t)

    # Criar o barramento ao qual nós estarão conectados
    barramento = MeioTransmissao(escalonador)

    # Criar nós configurando os parâmetros das transmissões.
    # O nó 0 é o receptor; os demais são os transmissores.
    no = []
    for i in range(0, len(args.pos)):
    
        if i == 0:
            no.append(No(barramento, escalonador, i, None))
        else:
            no.append(No(barramento, escalonador, i, args.i, 0, args.s, args.r))

        # Conectar as interfaces dos nós ao barramento
        barramento.conectaInterface(no[i].getInterface(), args.pos[i])

    # Executar simulação até o fim
    escalonador.executa()

    # Imprimir estatísticas do receptor
    print("\nEstatísticas do nó receptor:\n")
    no[0].getInterface().sumarizaEstatisticas()

# Programa principal
main()
