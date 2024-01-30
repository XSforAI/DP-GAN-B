# ------------------------------------------------------------------------------
# Copyright (c) Tencent
# Licensed under the GPLv3 License.
# Created by Kai Ma (makai0324@gmail.com)
# ------------------------------------------------------------------------------

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import functools
import math
from lib.model.nets.generator.encoder_decoder_utils import *
from lib.model.nets.generator.double_attention_no_AdaIN import *
from lib.model.nets.generator.self_attention import *
from lib.model.nets.generator.F import *
from lib.model.nets.generator.swin_attention import *
#input_shape=(128,128)
def UNetLike_DownStep5(input_shape, encoder_input_channels, decoder_output_channels, decoder_out_activation, encoder_norm_layer, decoder_norm_layer, upsample_mode, decoder_feature_out=False):
  # 64, 32, 16, 8, 4
  encoder_block_list = [6, 12, 24, 16, 6]
  decoder_block_list = [1, 2, 2, 2, 2, 0]
  growth_rate = 32
  encoder_channel_list = [64]
  decoder_channel_list = [16, 16, 32, 64, 128, 256]
  decoder_begin_size = input_shape // pow(2, len(encoder_block_list))
  return UNetLike_DenseDimensionNet(input_shape, encoder_input_channels, decoder_output_channels, decoder_begin_size, encoder_block_list, decoder_block_list, growth_rate, encoder_channel_list, decoder_channel_list, decoder_out_activation, encoder_norm_layer, decoder_norm_layer, upsample_mode, decoder_feature_out)

def UNetLike_DownStep5_3(input_shape, encoder_input_channels, decoder_output_channels, decoder_out_activation, encoder_norm_layer, decoder_norm_layer, upsample_mode, decoder_feature_out=False):
  # 64, 32, 16, 8, 4
  encoder_block_list = [6, 12, 32, 32, 12]
  decoder_block_list = [3, 3, 3, 3, 3, 1]
  growth_rate = 32
  encoder_channel_list = [64]
  decoder_channel_list = [16, 32, 64, 64, 128, 256]
  decoder_begin_size = input_shape // pow(2, len(encoder_block_list))
  return UNetLike_DenseDimensionNet(input_shape,encoder_input_channels, decoder_output_channels, decoder_begin_size, encoder_block_list, decoder_block_list, growth_rate, encoder_channel_list, decoder_channel_list, decoder_out_activation, encoder_norm_layer, decoder_norm_layer, upsample_mode, decoder_feature_out)

class UNetLike_DenseDimensionNet(nn.Module):
  def __init__(self,input_shape, encoder_input_channels, decoder_output_channels, decoder_begin_size, encoder_block_list, decoder_block_list, growth_rate, encoder_channel_list, decoder_channel_list, decoder_out_activation, encoder_norm_layer=nn.BatchNorm2d, decoder_norm_layer=nn.BatchNorm3d, upsample_mode='nearest', decoder_feature_out=False):
    super(UNetLike_DenseDimensionNet, self).__init__()
    self.input_shape = input_shape
    self.decoder_channel_list = decoder_channel_list
    self.decoder_block_list = decoder_block_list
    self.n_downsampling = len(encoder_block_list)
    self.decoder_begin_size = decoder_begin_size
    self.decoder_feature_out = decoder_feature_out
    activation = nn.ReLU(True)
    bn_size = 4
    ##########
    ##############
    # Encoder
    ##############
    if type(encoder_norm_layer) == functools.partial:
      use_bias = encoder_norm_layer.func == nn.InstanceNorm2d
    else:
      use_bias = encoder_norm_layer == nn.InstanceNorm2d
    ##############
    #编码第一层
    ##############
    #encoder_input_channels=1
    #encoder_channel_list[0]=64
    encoder_layers0 = [
      nn.ReflectionPad2d(3),
      #nn.Conv2d(encoder_input_channels, encoder_channel_list[0], kernel_size=7, padding=0, bias=use_bias),
      nn.Conv2d(encoder_input_channels, encoder_input_channels, kernel_size=7, padding=0, groups=encoder_input_channels, bias=use_bias),
      nn.Conv2d(encoder_input_channels, encoder_channel_list[0], kernel_size=1, padding=0, bias=use_bias),
      encoder_norm_layer(encoder_channel_list[0]),
      activation
    ]
    self.encoder_layer = nn.Sequential(*encoder_layers0)

    num_input_channels = encoder_channel_list[0]
    #print(input_shape)
    for index, channel in enumerate(encoder_block_list):
      # pooling
      down_layers = [
        #############归一化层，使网络平稳，有利于网络的训练
        encoder_norm_layer(num_input_channels),
        #############激活函数，用于在线性提取中引入非线性
        activation,
        #num_input_channels=64
        #num_ouput_channels=64
        #nn.Conv2d(num_input_channels, num_input_channels, kernel_size=3, stride=2, padding=1, bias=use_bias),
        #############通过步幅为2的操作减小特征图的尺寸，同时通道数保持不变
      ]
      down_layers+=[
        #nn.Conv2d(num_input_channels, num_input_channels, kernel_size=3, stride=2, padding=1, bias=use_bias),
        nn.Conv2d(num_input_channels, num_input_channels, kernel_size=3, stride=2, padding=1, groups=num_input_channels, bias=use_bias),
        nn.Conv2d(num_input_channels, num_input_channels, kernel_size=1, stride=1, padding=0, bias=use_bias),
      ]

      '''
      if index==0 or index==1:
        down_layers+=[
            #Block(dim=num_input_channels,num_heads=2),
            #AIA_1(num_input_channels).cuda(), 
            #Pos_att(num_input_channels),
            AIA(num_input_channels).cuda(), 
            #CAT(num_input_channels).cuda(),           
            #nn.Conv2d(num_input_channels, num_input_channels, kernel_size=3, stride=2, padding=1, bias=use_bias), 
        ]
      else:
        down_layers+=[
            #Block(dim=num_input_channels,num_heads=2),
            AIA_1(num_input_channels).cuda(), 
            #Pos_att(num_input_channels),
            #AIA(num_input_channels).cuda(), 
            #CAT(num_input_channels).cuda(),           
            #nn.Conv2d(num_input_channels, num_input_channels, kernel_size=3, stride=2, padding=1, bias=use_bias), 
        ]
      '''
      '''
      SwinIR(img_size=input_shape//pow(2,index), patch_size=4, in_chans=num_input_channels,
                embed_dim=num_input_channels, depths=[6, 6, 6, 6], num_heads=[8, 8, 8, 8],
                window_size=4, mlp_ratio=4., qkv_bias=True, qk_scale=None,
                drop_rate=0., attn_drop_rate=0., drop_path_rate=0.1,
                norm_layer=nn.LayerNorm, ape=False, patch_norm=True,
                use_checkpoint=False, upscale=2, img_range=1., upsampler='pixelshuffledirect', resi_connection='1conv'
              ),
        nn.Conv2d(num_input_channels, num_input_channels + encoder_block_list[index] * growth_rate, kernel_size=3, stride=2, padding=1, bias=use_bias),
      '''
    

      down_layers +=[
        #############这是一个 Python 中的列表拼接操作，encoder_block_list[index]决定了在密集块中使用多少个卷积层
        #############num_input_channels这是输入到密集块的通道数，也就是前一个层的输出通道数。
        #############growth_rate：生长率，指定了每个密集块中每个卷积层的输出通道数。32
        #encoder_block_list = [6, 12, 24, 32, 12]
        #growth_rate = 32
        Dense_2DBlock(encoder_block_list[index], num_input_channels, bn_size, growth_rate, encoder_norm_layer, activation, use_bias), 
      ]
      #print('img_size:',input_shape//pow(2,index))
      ################这一行更新了下一个密集块的输入通道数。它计算了下一个密集块的输入通道数，这是当前输入通道数与当前密集块中卷积层的输出通道数之和。
      num_input_channels = num_input_channels + encoder_block_list[index] * growth_rate

      #num_input_channels: 256
      #num_input_channels: 512
      #num_input_channels: 1024
      #num_input_channels: 1024
      #num_input_channels: 704

      # feature maps are compressed into 1 after the lastest downsample layers
      if index == (self.n_downsampling-1):
        down_layers += [
          nn.AdaptiveAvgPool2d(1)
        ]
      else:
        num_out_channels = num_input_channels // 2
        down_layers += [
          encoder_norm_layer(num_input_channels),
          activation,
          #nn.Conv2d(num_input_channels, num_out_channels, kernel_size=1, stride=1, padding=0, bias=use_bias),
          nn.Conv2d(num_input_channels, num_input_channels, kernel_size=1, stride=1, padding=0, groups=num_input_channels,bias=False),
          nn.Conv2d(num_input_channels, num_out_channels, kernel_size=1, stride=1, padding=0, bias=use_bias),
        ]
        num_input_channels = num_out_channels
      encoder_channel_list.append(num_input_channels)
      setattr(self, 'encoder_layer' + str(index), nn.Sequential(*down_layers))

    ##############
    # Linker
    ##############
    if type(decoder_norm_layer) == functools.partial:
      use_bias = decoder_norm_layer.func == nn.InstanceNorm3d
    else:
      use_bias = decoder_norm_layer == nn.InstanceNorm3d

    # linker FC
    # apply fc to link 2d and 3d
    self.base_link = nn.Sequential(*[
      ##############64**3*256 
      nn.Linear(encoder_channel_list[-1], decoder_begin_size**3*decoder_channel_list[-1]),
      ##############是 PyTorch 中用于实现Dropout正则化的层。Dropout 是一种用于防止神经网络过拟合的正则化技术
      nn.Dropout(0.5),
      activation
    ])

    for index, channel in enumerate(encoder_channel_list[:-1]):
      in_channels = channel
      out_channels = decoder_channel_list[index]
      link_layers = [
        Dimension_UpsampleCutBlock(in_channels, out_channels, encoder_norm_layer, decoder_norm_layer, activation, use_bias)
      ]
      setattr(self, 'linker_layer' + str(index), nn.Sequential(*link_layers))

    ##############
    # Decoder
    ##############
    for index, channel in enumerate(decoder_channel_list[:-1]):
      out_channels = channel
      in_channels = decoder_channel_list[index+1]
      decoder_layers = []
      decoder_compress_layers = []
      if index != (len(decoder_channel_list) - 2):
        decoder_compress_layers += [
          #nn.Conv3d(in_channels * 2, in_channels, kernel_size=3, padding=1, bias=use_bias),
          nn.Conv3d(in_channels * 2, in_channels * 2, kernel_size=3, padding=1, groups=in_channels * 2, bias=False),
          nn.Conv3d(in_channels * 2, in_channels, kernel_size=1, padding=0, bias=use_bias),
          decoder_norm_layer(in_channels),
          activation
        ]
        for _ in range(decoder_block_list[index+1]):
          decoder_layers += [
            #nn.Conv3d(in_channels, in_channels, kernel_size=3, padding=1, bias=use_bias),
            nn.Conv3d(in_channels, in_channels, kernel_size=3, padding=1, groups=in_channels, bias=False),
            nn.Conv3d(in_channels, in_channels, kernel_size=1, padding=0, bias=use_bias),
            decoder_norm_layer(in_channels),
            activation
          ]
      decoder_layers += [
        Upsample_3DUnit(3, in_channels, out_channels, decoder_norm_layer, scale_factor=2, upsample_mode=upsample_mode, activation=activation, use_bias=use_bias)
      ]
      # If decoder_feature_out is True, compressed feature after upsampling and concatenation
      # can be obtained.
      if decoder_feature_out:
        setattr(self, 'decoder_compress_layer' + str(index), nn.Sequential(*decoder_compress_layers))
        setattr(self, 'decoder_layer' + str(index), nn.Sequential(*decoder_layers))
      else:
        setattr(self, 'decoder_layer' + str(index), nn.Sequential(*(decoder_compress_layers+decoder_layers)))
    # last decode
    decoder_layers = []
    decoder_compress_layers = [
      #nn.Conv3d(decoder_channel_list[0] * 2, decoder_channel_list[0], kernel_size=3, padding=1, bias=use_bias),
      nn.Conv3d(decoder_channel_list[0] * 2, decoder_channel_list[0] * 2, kernel_size=3, padding=1, groups=decoder_channel_list[0] * 2, bias=False),
      nn.Conv3d(decoder_channel_list[0] * 2, decoder_channel_list[0], kernel_size=1, padding=0, bias=use_bias),
      decoder_norm_layer(decoder_channel_list[0]),
      activation
    ]
    for _ in range(decoder_block_list[0]):
      decoder_layers += [
        #nn.Conv3d(decoder_channel_list[0], decoder_channel_list[0], kernel_size=3, padding=1, bias=use_bias),
        nn.Conv3d(decoder_channel_list[0], decoder_channel_list[0], kernel_size=3, padding=1, groups=decoder_channel_list[0], bias=False),
        nn.Conv3d(decoder_channel_list[0], decoder_channel_list[0], kernel_size=1, padding=0, bias=use_bias),
        decoder_norm_layer(decoder_channel_list[0]),
        activation
      ]
    if decoder_feature_out:
      setattr(self, 'decoder_compress_layer' + str(-1), nn.Sequential(*decoder_compress_layers))
      setattr(self, 'decoder_layer' + str(-1), nn.Sequential(*decoder_layers))
    else:
      setattr(self, 'decoder_layer' + str(-1), nn.Sequential(*(decoder_compress_layers + decoder_layers)))

    self.decoder_layer = nn.Sequential(*[
      #nn.Conv3d(decoder_channel_list[0], decoder_output_channels, kernel_size=7, padding=3, bias=use_bias),
      nn.Conv3d(decoder_channel_list[0], decoder_channel_list[0], kernel_size=7, padding=3, groups=decoder_channel_list[0],bias=False),
      nn.Conv3d(decoder_channel_list[0], decoder_output_channels, kernel_size=1, padding=0, bias=use_bias),
      decoder_out_activation()
    ])
  #############神经网络模型的前向传播算法，用于网络的前向传播
  def forward(self, input):
    
    encoder_feature = self.encoder_layer(input)
    next_input = encoder_feature
    ###########循环下采样操作
    for i in range(self.n_downsampling):
      ##########这一行代码根据当前循环的索引 i 动态地将一个名为 linker_layer 的层应用到 next_input 上，
      ##########并将结果存储在名为 feature_linker<i> 的属性中。这个操作似乎是为了在下采样的过程中将中间特征存储下来以供后面的上采样使用。
      #print('feature_linker_input.shape:',next_input.shape)
      setattr(self, 'feature_linker' + str(i), getattr(self, 'linker_layer' + str(i))(next_input))
      ##########通过编码器层将 next_input 进行前向传播，更新 next_input
      next_input = getattr(self, 'encoder_layer'+str(i))(next_input)
    ##########在下采样循环结束后，将 next_input 展平并通过 base_link 层传播。这个层似乎是用来将特征进一步转换或连接到其他部分。
    next_input = self.base_link(next_input.view(next_input.size(0), -1))
    ##########将 next_input 重新变形，以适应解码器部分的输入大小。
    next_input = next_input.view(next_input.size(0), self.decoder_channel_list[-1], self.decoder_begin_size, self.decoder_begin_size, self.decoder_begin_size)

    for i in range(self.n_downsampling - 1, -2, -1):
      ############如果 i 是最后一层（self.n_downsampling - 1），则应用解码器层和可能的压缩层。
      if i == (self.n_downsampling - 1):
        
        if self.decoder_feature_out:
          next_input = getattr(self, 'decoder_layer' + str(i))(getattr(self, 'decoder_compress_layer' + str(i))(next_input))
        else:
          next_input = getattr(self, 'decoder_layer' + str(i))(next_input)
      ##############如果 i 不是最后一层，将当前的 next_input 与前面保存的 feature_linker 连接起来，然后应用解码器层。
      else:
        if self.decoder_feature_out:
          next_input = getattr(self, 'decoder_layer' + str(i))(getattr(self, 'decoder_compress_layer' + str(i))(torch.cat((next_input, getattr(self, 'feature_linker'+str(i+1))), dim=1)))
        else:
          next_input = getattr(self, 'decoder_layer' + str(i))(torch.cat((next_input, getattr(self, 'feature_linker'+str(i+1))), dim=1))

    return self.decoder_layer(next_input)

#>>>>>>>>>>>>>>>>>>>
#view1Order=opt.CTOrder_Xray1 CTOrder_Xray1: [0, 1, 3, 2, 4]
#view2Order=opt.CTOrder_Xray2 CTOrder_Xray2: [0, 1, 4, 2, 3]
#decoder_output_channels=output_nc,
#decoder_out_activation=activation_layer,
#decoder_block_list=[1, 1, 1, 1, 1, 0]
#backToSub=True
class MultiView_UNetLike_DenseDimensionNet(nn.Module):
  def __init__(self, view1Model, view2Model, view1Order, view2Order, backToSub, decoder_output_channels, decoder_out_activation, decoder_block_list=None, decoder_norm_layer=nn.BatchNorm3d, upsample_mode='nearest'):
    super(MultiView_UNetLike_DenseDimensionNet, self).__init__()
    self.view1Model = view1Model
    self.view2Model = view2Model
    self.view1Order = view1Order
    self.view2Order = view2Order
    self.backToSub = backToSub
    self.n_downsampling = view2Model.n_downsampling
    self.decoder_channel_list = view2Model.decoder_channel_list
    if decoder_block_list is None:
      self.decoder_block_list = view2Model.decoder_block_list
    else:
      self.decoder_block_list = decoder_block_list

    activation = nn.ReLU(True)
    if type(decoder_norm_layer) == functools.partial:
      use_bias = decoder_norm_layer.func == nn.InstanceNorm3d
    else:
      use_bias = decoder_norm_layer == nn.InstanceNorm3d
    ##############
    # Decoder
    ##############

    #decoder_channel_list = [16, 16, 32, 64, 128, 256]
    #decoder_block_list = [1, 2, 2, 2, 2, 0]
    #self.decoder_channel_list[:-1]:
    #选择列表 self.decoder_channel_list 中从第一个元素（索引为0）到倒数第二个元素（不包括最后一个元素）的所有元素
    #index=0,1,2,3,4
    for index, channel in enumerate(self.decoder_channel_list[:-1]):
      out_channels = channel
      in_channels = self.decoder_channel_list[index + 1]
      decoder_layers = []
      decoder_compress_layers = []
      if index != (len(self.decoder_channel_list) - 2):
        #Up-Conv
        #compress_layers
        decoder_compress_layers += [
          #nn.Conv3d(in_channels * 2, in_channels, kernel_size=3, padding=1, bias=use_bias),
          nn.Conv3d(in_channels * 2, in_channels * 2, kernel_size=3, padding=1, groups=in_channels * 2,bias=False),
          nn.Conv3d(in_channels * 2, in_channels, kernel_size=1, padding=0, bias=use_bias),
          decoder_norm_layer(in_channels),
          activation
        ]
        for _ in range(self.decoder_block_list[index+1]):
          #decoder_layers
          decoder_layers += [
            #nn.Conv3d(in_channels, in_channels, kernel_size=3, padding=1, bias=use_bias),
            nn.Conv3d(in_channels, in_channels, kernel_size=3, padding=1, groups=in_channels,bias=False),
            nn.Conv3d(in_channels, in_channels, kernel_size=1, padding=0, bias=use_bias),

            decoder_norm_layer(in_channels),
            activation
          ]

      decoder_layers += [
        #kernel_size=3
        Upsample_3DUnit(3, in_channels, out_channels, decoder_norm_layer, scale_factor=2, upsample_mode=upsample_mode,
                        activation=activation, use_bias=use_bias)
      ]
      #combine
      setattr(self, 'decoder_layer' + str(index), nn.Sequential(*(decoder_compress_layers + decoder_layers)))
    # last decode
    decoder_layers = []
    #compress_layer
    decoder_compress_layers = [
      #nn.Conv3d(self.decoder_channel_list[0] * 2, self.decoder_channel_list[0], kernel_size=3, padding=1, bias=use_bias),
      nn.Conv3d(self.decoder_channel_list[0] * 2, self.decoder_channel_list[0] * 2, kernel_size=3, padding=1, groups=self.decoder_channel_list[0] * 2,bias=False),
      nn.Conv3d(self.decoder_channel_list[0] * 2, self.decoder_channel_list[0], kernel_size=1, padding=0, bias=use_bias),
      decoder_norm_layer(self.decoder_channel_list[0]),
      activation
    ]
    #decoder_list
    for _ in range(self.decoder_block_list[0]):
      decoder_layers += [
        #nn.Conv3d(self.decoder_channel_list[0], self.decoder_channel_list[0], kernel_size=3, padding=1, bias=use_bias),
        nn.Conv3d(self.decoder_channel_list[0], self.decoder_channel_list[0], kernel_size=3, padding=1, groups=self.decoder_channel_list[0],bias=False),
        nn.Conv3d(self.decoder_channel_list[0], self.decoder_channel_list[0], kernel_size=1, padding=0, bias=use_bias),
        decoder_norm_layer(self.decoder_channel_list[0]),
        activation
      ]
    
    setattr(self, 'decoder_layer' + str(-1), nn.Sequential(*(decoder_compress_layers + decoder_layers)))
    #16-1
    self.decoder_layer = nn.Sequential(*[
      #nn.Conv3d(self.decoder_channel_list[0], decoder_output_channels, kernel_size=7, padding=3, bias=use_bias),
      nn.Conv3d(self.decoder_channel_list[0], self.decoder_channel_list[0], kernel_size=7, padding=3, groups=self.decoder_channel_list[0],bias=False),
      nn.Conv3d(self.decoder_channel_list[0], decoder_output_channels, kernel_size=1, padding=0, bias=use_bias),
      decoder_out_activation()
    ])
    #fushion 
    self.transposed_layer = Transposed_And_Add(view1Order, view2Order)

  
  def forward(self, input):
    # only support two views
    assert len(input) == 2
    # View 1 encoding process
    view1_encoder_feature = self.view1Model.encoder_layer(input[0])
    #print('input[0].shape',input[0].shape)
    #print('FFt__encoder_feature.shape',FFt__encoder_feature.shape)
    view1_next_input = view1_encoder_feature
    #print(view1_next_input.device)
    
    #FFt=F(input[0]).cuda()
    #FFt__encoder_feature = self.view1Model.encoder_layer(input[0])
    #FFt__encoder_feature = FFt__encoder_feature.to(FFt.device)
    '''
    B,C,H,W=view1_next_input.shape

    layer=Block(dim=C, num_heads=2)
    x=layer(view1_next_input).to('cuda')

    result=torch.cat([x,view1_next_input],dim=1)
    conv_layer=conv1(2*C,C)
    view1_next_input_1=conv_layer(result)
    norm_layer=nn.LayerNorm(C).to('cuda')
    mlp_layer=Mlp(in_features= C, act_layer=nn.GELU, drop=0.).to('cuda')
    view1_next_input_1=view1_next_input_1.reshape(-1,64)
    view1_next_input=view1_next_input+mlp_layer(norm_layer(view1_next_input_1)).reshape(B,C,H,W)
    '''
    #print(view1_next_input)
    #print('view1_next_input.shape:',view1_next_input.shape)
    for i in range(self.view1Model.n_downsampling):
      setattr(self.view1Model, 'feature_linker' + str(i), getattr(self.view1Model, 'linker_layer' + str(i))(view1_next_input))
      view1_next_input = getattr(self.view1Model, 'encoder_layer'+str(i))(view1_next_input)
      #print('i:',i)
      '''
      
      
      if i==0 or i==1 :
        
        #view1_next_input = view1_next_input.to('cuda')
        FFt__encoder_feature = view1_next_input
        #FFt__encoder_feature = FFt__encoder_feature.to('cuda')

        B,C,H,W=FFt__encoder_feature.shape
        layer=Block(dim=C, num_heads=2)
        x=layer(FFt__encoder_feature).to('cuda')
        result=torch.cat([x,view1_next_input],dim=1)
        conv_layer=conv1(2*C,C)
        view1_next_input_1=conv_layer(result)
        norm_layer=nn.LayerNorm(C).to('cuda')
        mlp_layer=Mlp(in_features= C, act_layer=nn.GELU, drop=0.).to('cuda')
        view1_next_input_1=view1_next_input_1.reshape(-1,C)
        view1_next_input=view1_next_input+mlp_layer(norm_layer(view1_next_input_1)).reshape(B,C,H,W)
      '''
      #view1_next_input = view1_next_input.to('cuda')
      #print('view1_next_input.shape:',view1_next_input.shape)
    # View 2 encoding process
    view2_encoder_feature = self.view2Model.encoder_layer(input[1])
    view2_next_input = view2_encoder_feature
    '''
    FFt_1=F(input[1]).cuda()
    FFt__encoder_feature_1 = self.view1Model.encoder_layer(FFt_1)
    FFt__encoder_feature_1 = FFt__encoder_feature_1.to(FFt_1.device)
    B,C,H,W=FFt__encoder_feature_1.shape
    layer=Block(dim=C, num_heads=2)
    x=layer(FFt__encoder_feature_1).to('cuda')

    result=torch.cat([x,view2_next_input],dim=1)
    conv_layer=conv1(2*C,C)
    view2_next_input=conv_layer(result)
    '''
    for i in range(self.view2Model.n_downsampling):
      setattr(self.view2Model, 'feature_linker' + str(i),
              getattr(self.view2Model, 'linker_layer' + str(i))(view2_next_input))
      view2_next_input = getattr(self.view2Model, 'encoder_layer' + str(i))(view2_next_input)

      '''
      FFt__encoder_feature_1 = getattr(self.view1Model, 'encoder_layer'+str(i))(FFt__encoder_feature_1)
      B,C,H,W=FFt__encoder_feature_1.shape
      layer=Block(dim=C, num_heads=2)
      x=layer(FFt__encoder_feature_1).to('cuda')
      result=torch.cat([x,view2_next_input],dim=1)
      conv_layer=conv1(2*C,C)
      view2_next_input=conv_layer(result)
      '''

    # View 1 decoding process Part1
    view1_next_input = self.view1Model.base_link(view1_next_input.view(view1_next_input.size(0), -1))
    view1_next_input = view1_next_input.view(view1_next_input.size(0), self.view1Model.decoder_channel_list[-1], self.view1Model.decoder_begin_size,
                                             self.view1Model.decoder_begin_size, self.view1Model.decoder_begin_size)
    #print('view1_next_input_1.shape:',view1_next_input.shape)
    # View 2 decoding process Part1
    view2_next_input = self.view2Model.base_link(view2_next_input.view(view2_next_input.size(0), -1))
    view2_next_input = view2_next_input.view(view2_next_input.size(0), self.view2Model.decoder_channel_list[-1], self.view2Model.decoder_begin_size,
                                             self.view2Model.decoder_begin_size, self.view2Model.decoder_begin_size)

    view_next_input = None
    # View 1 and 2 decoding process Part2
    #在每次循环中，i 的值会从 self.n_downsampling - 1 开始递减，直到 -1
    #表示循环将在 self.n_downsampling - 1 这个值到 -2 这个值之间的整数范围内进行迭代。这个迭代会从 self.n_downsampling - 1 开始，递减 -1 直到 -2，然后循环结束。
    for i in range(self.n_downsampling - 1, -2, -1):
      if i == (self.n_downsampling - 1):
        view1_next_input = getattr(self.view1Model, 'decoder_compress_layer' + str(i))(view1_next_input)
        #print('view1_next_input.shape:',view1_next_input.shape)
        view2_next_input = getattr(self.view2Model, 'decoder_compress_layer' + str(i))(view2_next_input)
        ########### MultiView Fusion
        # Method One: Fused feature back to sub-branch
        if self.backToSub:
          view_avg = self.transposed_layer(view1_next_input, view2_next_input)/2
          view1_next_input = view_avg.permute(*self.view1Order)
          #print('view1_next_input.shape:',view1_next_input.shape)
          view2_next_input = view_avg.permute(*self.view2Order)
          view_next_input = getattr(self, 'decoder_layer' + str(i))(view_avg)
        # Method Two: Fused feature only used in main-branch
        else:
          view_avg = self.transposed_layer(view1_next_input, view2_next_input) /2
          view_next_input = getattr(self, 'decoder_layer' + str(i))(view_avg)
        ###########
        view1_next_input = getattr(self.view1Model, 'decoder_layer' + str(i))(view1_next_input)
        #print('view1_next_input.shape:',view1_next_input.shape)
        view2_next_input = getattr(self.view2Model, 'decoder_layer' + str(i))(view2_next_input)
      else:
        #print('view1_next_input.shape:',view1_next_input.shape)
        #print('getattr:',getattr(self.view1Model, 'feature_linker' + str(i + 1)).shape)
        #view1Model=UNetLike_DownStep5(input_shape=encoder_input_shape[0], encoder_input_channels=encoder_input_nc, decoder_output_channels=output_nc, decoder_out_activation=activation_layer, encoder_norm_layer=encoder_norm_layer, decoder_norm_layer=decoder_norm_layer, upsample_mode='transposed', decoder_feature_out=True)
        view1_next_input = getattr(self.view1Model, 'decoder_compress_layer' + str(i))(torch.cat((view1_next_input, getattr(self.view1Model, 'feature_linker' + str(i + 1))), dim=1))
        view2_next_input = getattr(self.view2Model, 'decoder_compress_layer' + str(i))(torch.cat((view2_next_input, getattr(self.view2Model, 'feature_linker' + str(i + 1))), dim=1))
        ########### MultiView Fusion
        # Method One: Fused feature back to sub-branch
        if self.backToSub:
          view_avg = self.transposed_layer(view1_next_input, view2_next_input)/2
          view1_next_input = view_avg.permute(*self.view1Order)
          view2_next_input = view_avg.permute(*self.view2Order)
          view_next_input = getattr(self, 'decoder_layer' + str(i))(torch.cat((view_avg, view_next_input), dim=1))
        # Method Two: Fused feature only used in main-branch
        else:
          view_avg = self.transposed_layer(view1_next_input, view2_next_input) / 2
          view_next_input = getattr(self, 'decoder_layer' + str(i))(torch.cat((view_avg, view_next_input), dim=1))
        ###########
        view1_next_input = getattr(self.view1Model, 'decoder_layer' + str(i))(view1_next_input)
        view2_next_input = getattr(self.view2Model, 'decoder_layer' + str(i))(view2_next_input)


    return self.view1Model.decoder_layer(view1_next_input), self.view2Model.decoder_layer(view2_next_input), self.decoder_layer(view_next_input)