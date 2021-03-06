import random

import torch
import torch.nn.functional as F

class Train_Network(object):
    def __init__(self, lm, index2word, max_length=20):
        self.lm = lm
        self.index2word = index2word
        self.max_length = max_length
        self.use_cuda = torch.cuda.is_available()

    def repackage_hidden(self, hidden):
        ''' Wraps hidden states in new Tensors, to detach them from their history. '''
        if isinstance(hidden, torch.Tensor): return hidden.detach()
        else: return tuple(self.repackage_hidden(v) for v in hidden)

    def train(self, input_variables, input_lengths, target_variables, lm_hidden, criterion, lm_optimizer):
        ''' Pad all tensors in this batch to same length. '''
        input_variables = torch.nn.utils.rnn.pad_sequence(input_variables)
        target_variables = torch.nn.utils.rnn.pad_sequence(target_variables)

        lm_hidden = self.repackage_hidden(lm_hidden)

        batch_size = input_variables.size()[1]
        target_length = target_variables.size()[0]

        loss = 0

        lm_outputs, lm_hidden = self.lm(input_variables, input_lengths, lm_hidden)

        loss += criterion(lm_outputs, target_variables.permute(1, 0))

        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.lm.parameters(), 0.25)
        lm_optimizer.step()

        lm_optimizer.zero_grad()
        return loss.item() / target_length, lm_hidden

    def evaluate_and_decode(self, input_variables, seed_length):
        with torch.no_grad():
            ''' Pad all tensors in this batch to same length. '''
            input_variables = torch.nn.utils.rnn.pad_sequence(input_variables)

            batch_size = input_variables.size()[1]
            lm_inputs = input_variables[0, :].view(1, -1)
            lm_hidden = self.lm.init_hidden(batch_size)

            output_words = [[] for i in range(batch_size)]

            for di in range(self.max_length):
                lm_outputs, lm_hidden = self.lm.predict(lm_inputs, lm_hidden)

                lm_outputs = F.log_softmax(lm_outputs, dim=1)
                topv, topi = lm_outputs.data.topk(1)
                for i, ind in enumerate(topi[0]):
                    output_words[i].append(self.index2word[ind])

                if di+1 < seed_length:
                    lm_inputs = input_variables[di+1, :].view(1, -1)
                else:
                    lm_inputs = topi.permute(1, 0)
                    if self.use_cuda: lm_inputs = lm_inputs.cuda()

        return output_words

    def evaluate(self, input_variables, input_lengths, target_variables, lm_hidden, criterion):
        with torch.no_grad():
            ''' Pad all tensors in this batch to same length. '''
            input_variables = torch.nn.utils.rnn.pad_sequence(input_variables)
            target_variables = torch.nn.utils.rnn.pad_sequence(target_variables)

            lm_hidden = self.repackage_hidden(lm_hidden)

            batch_size = input_variables.size()[1]
            target_length = target_variables.size()[0]

            loss = 0

            lm_outputs, lm_hidden = self.lm(input_variables, input_lengths, lm_hidden)
            loss += criterion(lm_outputs, target_variables.permute(1, 0))

            return loss.item() / target_length, lm_hidden
