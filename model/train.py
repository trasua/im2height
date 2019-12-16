import torch
import torch.nn as nn
import torch.optim as optim
from model.helper.utils import EarlyStopping, Logger
from model.dataloader import trainloader, validloader
import time
from model.metric import ssim, SSIM
from torch.utils.tensorboard import SummaryWriter


def train(net, num_epochs=100, model_name='im2height', learning_rate=1e-4):
    use_gpu = torch.cuda.is_available()
    device  = 'gpu:0' if use_gpu else 'cpu'
    if use_gpu:
        print('Using CUDA')
        net.cuda()

    dataloader = {'train': trainloader(), 'val': validloader()}
    train_size = len(dataloader['train'])
    valid_size = len(dataloader['val'])
    
    criterion = nn.L1Loss()
    optimizer = optim.Adam(net.parameters(), lr=learning_rate)

    train_writer = SummaryWriter(log_dir='logs-tensorboard/train')
    val_writer = SummaryWriter(log_dir='logs-tensorboard/val')
    es = EarlyStopping(mode='min', patience=10)
    since = time.time()

    best_loss = 0.0

    for epoch in range(num_epochs):
        start = time.time()
        print("Epoch {}/{}".format(epoch, num_epochs))
        print('-' * 10)

        for phase in ['train', 'val']:
            if phase == 'train':
                net.train()
            else:
                net.eval()

            running_loss = 0.0
            running_ssim = 0.0

            for image, mask in dataloader[phase]:
                image = image.to(device)
                mask = mask.to(device)

                optimizer.zero_grad()
                with torch.set_grad_enabled(phase == 'train'):
                    output = net(image)
                    loss = criterion(output, mask)
                    ssim_value = ssim(output, mask)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item()
                running_ssim += ssim_value.item()

                del image, label, output
                torch.cuda.empty_cache()

            data_size = train_size if phase == 'train' else valid_size
            epoch_loss = running_loss / data_size
            epoch_ssim = running_ssim / data_size

            print('{} -> Loss: {:.4f} Acc: {:.4f}'.format(phase, epoch_loss, epoch_acc))
            print('\ttime', time.time() - start)

            if phase == 'train':
                train_writer.add_scalar('L1Loss', epoch_loss, epoch)
                train_writer.add_scalar('SSIM', epoch_ssim, epoch)

            if phase == 'val':
                val_writer.add_scalar('L1Loss', epoch_loss, epoch)
                val_writer.add_scalar('SSIM', epoch_ssim, epoch)

                mae_loss = epoch_loss.cpu()
                if es.step(mae_loss):
                    time_elapsed = time.time() - since
                    print('Early Stopping')
                    print('Training complete in {:.0f}m {:.0f}s'.format(time_elapsed // 60, time_elapsed % 60))
                    print('Best val loss: {:4f}'.format(best_loss))
                    return

                if epoch_loss < best_loss:
                    best_loss = epoch_loss
                    print('Update best loss: {:4f}'.format(best_loss))
                    torch.save(net.state_dict(), '{}.pt'.format(model_name))
                


if __name__ == '__main__':
    i1 = torch.rand((1,1,256,256))
    i2 = torch.rand((1,1,256,256))

    loss = ssim(i1,i1)
    print(loss.item())