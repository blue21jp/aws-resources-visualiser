# ECR utilities
#
# 必須環境変数:
#   ECR_PROFILE     - AWSプロファイル名
#   IMAGE_NAME      - イメージ名:タグ
#   DOCKERFILE      - Dockerfileパス
#   ECR_REPO        - ECRリポジトリ名 (ecr_ls, ecr_rm用)
#
# オプション環境変数:
#   ECROPT          - docker buildオプション (デフォルト: 空文字列)

ecr_build:
    #!/usr/bin/env bash
    set -euo pipefail

    ECR_ACCOUNT_ID=$(aws sts get-caller-identity --profile ${ECR_PROFILE} --query 'Account' --output text)
    ECR_REGION=$(aws configure get region --profile ${ECR_PROFILE})
    ECR_BASE="${ECR_ACCOUNT_ID}.dkr.ecr.${ECR_REGION}.amazonaws.com"

    echo "ビルド対象イメージ: ${ECR_BASE}/${IMAGE_NAME}"
    echo "Dockerfile: ${DOCKERFILE}"

    hadolint ${DOCKERFILE}
    docker build -t ${ECR_BASE}/${IMAGE_NAME} -f ${DOCKERFILE} ${ECROPT:-} .

ecr_push:
    #!/usr/bin/env bash
    set -euo pipefail

    ECR_ACCOUNT_ID=$(aws sts get-caller-identity --profile ${ECR_PROFILE} --query 'Account' --output text)
    ECR_REGION=$(aws configure get region --profile ${ECR_PROFILE})
    ECR_BASE="${ECR_ACCOUNT_ID}.dkr.ecr.${ECR_REGION}.amazonaws.com"
    ECR_URL="https://${ECR_BASE}"

    echo "プッシュ対象イメージ: ${ECR_BASE}/${IMAGE_NAME}"

    aws ecr get-login-password --profile ${ECR_PROFILE} \
    | docker login --username AWS --password-stdin ${ECR_URL}

    docker push ${ECR_BASE}/${IMAGE_NAME}
    docker logout ${ECR_URL}

ecr_ls:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "リポジトリ情報:"
    aws ecr describe-repositories \
        --repository-names ${ECR_REPO} \
        --profile ${ECR_PROFILE}

    echo -e "\nイメージタグ一覧:"
    aws ecr list-images \
        --repository-name ${ECR_REPO} \
        --query 'imageIds[*].imageTag' \
        --output table \
        --profile ${ECR_PROFILE}

ecr_rm:
    #!/usr/bin/env bash
    set -euo pipefail

    ECR_ACCOUNT_ID=$(aws sts get-caller-identity --profile ${ECR_PROFILE} --query 'Account' --output text)
    ECR_REGION=$(aws configure get region --profile ${ECR_PROFILE})
    ECR_BASE="${ECR_ACCOUNT_ID}.dkr.ecr.${ECR_REGION}.amazonaws.com"

    echo "削除対象イメージ: ${ECR_BASE}/${IMAGE_NAME}"

    ECR_TAG=$(echo "${IMAGE_NAME}" | cut -d':' -f2)
    echo "タグ: ${ECR_TAG}"

    aws ecr batch-delete-image \
        --repository-name ${ECR_REPO} \
        --image-ids imageTag=${ECR_TAG} \
        --profile ${ECR_PROFILE} || echo "削除対象イメージが見つかりませんでした"
