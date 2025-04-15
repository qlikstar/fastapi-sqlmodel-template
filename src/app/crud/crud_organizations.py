from fastcrud import FastCRUD

from ..models.organization import Organization, OrganizationCreate, OrganizationUpdate, OrganizationUpdateInternal, OrganizationDelete

CRUDOrganization = FastCRUD[Organization, OrganizationCreate, OrganizationUpdate, OrganizationUpdateInternal, OrganizationDelete]
crud_organizations = CRUDOrganization(Organization)
