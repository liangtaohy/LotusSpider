#-*-coding:utf8-*-
#
# 样本为X, Y。X.shape=(m,d), Y.shape=(m, k)。d为X的维度，m样本数, k为分类标签数
# Weight: (k, d), b: (k,1) => theta: (k, d+1)
#

import numpy as np


def softmax(X):
    x = np.exp(X)
    p = np.sum(x, axis=1, keepdims=True)
    return x / p


def mini_batch(X, Y, batch_size):
    """
    mini batch iter

    :param X: input matrix
    :param Y: input label matrix
    :param batch_size: batch size
    :return: mini batch x, mini batch y
    """
    num_examples = len(X)
    indices = list(range(num_examples))
    np.random.shuffle(indices)
    for i in range(0, num_examples, batch_size):
        indexes = indices[i:min(i + batch_size, num_examples)]
        yield X[indexes, :], Y[indexes, :]


# theta: (k, d+1)
# xi: d+1 vector, x0 = 1
def h_elmentwise(theta, xi):
    e = np.exp(np.dot(theta, xi))
    return e / np.sum(e)


# theta: (k, d+1)
# X: (m, d+1), m is the number of samples. d is the dimension of input x. the extra one dimension is always be 1
# return: (m, k)
def h_vec(theta, X):
    """
    假设函数

    :param theta:
    :param X:
    :return:
    """
    eta = np.matmul(X, theta)
    eta = eta - np.reshape(np.amax(eta, axis=1), [-1, 1])
    x = np.exp(eta)
    return x / np.sum(x, axis=1, keepdims=True)


def sgd_vec(X_train, Y_train, theta, alpha, lamda=0):
    """
    随机梯度下降（支持mini batch）

    :param X_train: 训练样本
    :param Y_train: 分类标签
    :param theta: theta权重矩阵
    :param alpha: 学习速率
    :param lamda: 惩罚因子
    :return:
    """
    # mini batch sgd
    # 小批量随机梯度下降
    y_hat = h_vec(theta, X_train)
    diff = y_hat - Y_train
    for i in range(theta.shape[1]):
        theta[:, i] = theta[:, i] - alpha * np.squeeze(np.matmul(np.reshape(diff[:, i], [1, -1]), X_train)) + lamda * theta[:, i]
    return theta


def train(X_train, Y_train, theta, num_epochs, alpha, batch_size, lamda=0):
    for i in range(num_epochs):
        j = 0
        for x, y in mini_batch(X_train, Y_train, batch_size):
            theta = sgd_vec(x, Y_train=y, theta=theta, alpha=alpha, lamda=lamda)
            j += 1
        pred = np.argmax(h_vec(theta, X_train), axis=1)
        print("percentage correct: {0}".format(np.sum(pred == np.argmax(Y_train, axis=1)) / float(len(Y_train))))
    return theta


def predict(X, theta):
    """
    预测

    :param X: 输入样本
    :param theta: 权重矩阵
    :return:
    """
    X = np.insert(X, 0, values=np.ones(X.shape[0]), axis=1)
    predict_y = h_vec(theta=theta, X=X)
    return predict_y


def predic_y(X, theta):
    """
    预测

    :param X: 输入数据, shape=(m,d), m为样本数, d为维度
    :param theta: 参数矩阵
    :return:
    """
    X = np.insert(X, 0, values=np.ones(X.shape[0]), axis=1)
    return np.argmax(h_vec(theta, X), axis=1)


# 交叉熵损失函数
def cross_entropy(Y, Y_hat):
    M = Y.shape[0]
    y = np.choose(Y, Y_hat.T)
    return -(1/M) * np.sum(np.log(y))


def print_help():
    print('softmax_regression.py -s images.csv -L label.csv -m captcha.pickle')
    print('or: softmax_regression.py --source=images.csv --label=label.csv --model=captcha.pickle')
    sys.exit()


if __name__ == '__main__':
    import time
    import sys
    import getopt
    import pickle

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hs:L:m", ["help", "source=", "label=", "model="])
    except getopt.GetoptError:
        print "Error: softmax_regression.py -s images.csv -L label.csv -m captcha.pickle"
        sys.exit(1)

    source = None
    label = None
    model = None

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print_help()
        elif opt in ("-s", "--source"):
            source = arg
        elif opt in ("-L", "--label"):
            label = arg
        elif opt in ("-m", "--model"):
            model = arg

    if not source or not label or not model:
        print_help()

    # 单层全连接神经网络
    # Input layer: (d, 1), Output layer: (k, 1)
    # Weight Matrix: (k, d), bias vector: (k, 1) => \theta: (k, d+1)
    # Model: h = W * x + b

    X = np.ndfromtxt(source, delimiter=',')
    y_orig = np.ndfromtxt(label, delimiter=',', dtype=np.int8)

    d = X.shape[1]

    k = y_orig.shape[0]

    print "dimension: %i, class num: %i" % (d, k)

    rows = X.shape[0]

    shuffle_rows = np.arange(rows)
    np.random.shuffle(shuffle_rows)

    X = X[shuffle_rows, :]
    y_orig = y_orig[shuffle_rows]

    img_size = X.shape[1]
    num_class = k

    # Y one-hot vector
    Y = np.zeros([len(y_orig), num_class])
    Y[np.arange(len(y_orig)), y_orig] = 1

    # X维度从d扩展到d+1，其中，第0维的值为1
    X = np.insert(X, 0, values=np.ones(X.shape[0]), axis=1)
    num_epochs = int(len(Y) * 0.8)
    X_train = X[0:num_epochs, :]
    X_test = X[num_epochs:-1, :]
    y_train = Y[0:num_epochs]
    y_test = Y[num_epochs:-1]

    # theta weight matrix: (d + 1, k)
    theta = np.zeros([d + 1, k])

    batch_size = 100

    num_epochs = 120
    alpha = 0.001
    lamda = 0.005
    start = time.time()
    theta = train(X_train, y_train, theta=theta, num_epochs=num_epochs, alpha=alpha, batch_size=batch_size, lamda=lamda)
    end = time.time()
    print("time elapsed: {0} seconds".format(end - start))
    pred = np.argmax(h_vec(theta, X_test), axis=1)
    print("percentage correct: {0}".format(np.sum(pred == np.argmax(y_test, axis=1)) / float(len(y_test))))

    pickle.dump(theta, model)

    print "save model into " + model